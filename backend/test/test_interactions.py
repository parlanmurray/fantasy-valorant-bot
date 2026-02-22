"""P4 — Discord cog tests: ConfigCog, FantasyCog, StatsCog, helpers.
No live network or Discord token required; uses SQLite in-memory + AsyncMock.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session as SASession

import fantasyVCT.database as db
from fantasyVCT.database import Base
from fantasyVCT.interactions import (
	ConfigCog, FantasyCog, StatsCog, Category, add_spaces, POSITIONS,
)


AUTHOR_ID = "111111111111111111"


@pytest.fixture
def engine():
	eng = create_engine("sqlite:///:memory:")

	@event.listens_for(eng, "connect")
	def set_fk(dbapi_conn, _):
		cursor = dbapi_conn.cursor()
		cursor.execute("PRAGMA foreign_keys = ON")
		cursor.close()

	Base.metadata.create_all(eng)
	# Seed positions table (required FK for FantasyPlayer.position)
	with SASession(eng) as s:
		for pos_id, pos_name in POSITIONS.items():
			s.add(db.Position(id=pos_id, position=pos_name))
		s.commit()

	yield eng
	eng.dispose()


@pytest.fixture
def mock_bot(engine):
	bot = MagicMock()
	bot.cache = MagicMock()
	bot.sub_slots = 4
	bot.num_rounds = 5
	bot.draft_state = MagicMock()

	@contextmanager
	def make_session():
		with SASession(engine) as s:
			yield s

	bot.db_manager.create_session = make_session
	bot.scraper = MagicMock()
	return bot


@pytest.fixture
def ctx():
	c = MagicMock()
	c.send = AsyncMock()
	c.invoke = AsyncMock()
	c.message.author.id = AUTHOR_ID
	c.message.author.mention = f"<@!{AUTHOR_ID}>"
	return c


# ── helpers ───────────────────────────────────────────────────────────────────

class TestAddSpaces:
	def test_pads_short_string(self):
		result = "hi" + add_spaces("hi", 10)
		assert len(result) == 10

	def test_no_padding_when_already_long(self):
		assert add_spaces("hello world!", 5) == ""


class TestCategoryFromStr:
	def test_team(self):
		assert Category.from_str("TEAM") == Category.TEAM

	def test_teams_plural(self):
		assert Category.from_str("teams") == Category.TEAM

	def test_player(self):
		assert Category.from_str("PLAYER") == Category.PLAYER

	def test_invalid_raises(self):
		with pytest.raises(ValueError):
			Category.from_str("invalid")


# ── ConfigCog.register() ──────────────────────────────────────────────────────

async def test_register_already_registered(mock_bot, ctx, engine):
	with SASession(engine) as s:
		ft = db.FantasyTeam(name="ExistingTeam", abbrev="EXT")
		s.add(ft)
		s.flush()
		s.add(db.User(discord_id=AUTHOR_ID, fantasy_team_id=ft.id))
		s.commit()

	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "NEW", "New", "Team")
	ctx.send.assert_awaited_once_with("You have already registered a team.")


async def test_register_name_taken(mock_bot, ctx, engine):
	with SASession(engine) as s:
		s.add(db.FantasyTeam(name="Team Alpha", abbrev="OTH"))
		s.commit()

	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "TST", "Team", "Alpha")
	sent = ctx.send.call_args[0][0]
	assert "Team Alpha" in sent
	assert "taken" in sent


async def test_register_abbrev_taken(mock_bot, ctx, engine):
	with SASession(engine) as s:
		s.add(db.FantasyTeam(name="Other Team", abbrev="TST"))
		s.commit()

	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "TST", "My", "Team")
	sent = ctx.send.call_args[0][0]
	assert "TST" in sent
	assert "taken" in sent


async def test_register_success(mock_bot, ctx):
	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "TST", "Test", "Team")
	ctx.send.assert_awaited_once()
	sent = ctx.send.call_args[0][0]
	assert "TST" in sent
	assert "Test Team" in sent


# ── FantasyCog.draft() ────────────────────────────────────────────────────────

async def test_draft_not_started(mock_bot, ctx):
	mock_bot.draft_state.is_draft_started.return_value = False
	cog = FantasyCog(mock_bot)
	await cog.draft.callback(cog, ctx, "PlayerName")
	ctx.send.assert_awaited_once_with("Draft has not started yet!")


async def test_draft_not_your_turn(mock_bot, ctx):
	mock_bot.draft_state.is_draft_started.return_value = True
	mock_bot.draft_state.can_draft.return_value = False
	cog = FantasyCog(mock_bot)
	await cog.draft.callback(cog, ctx, "PlayerName")
	ctx.send.assert_awaited_once_with("It is not your turn yet!")


async def test_draft_player_not_found(mock_bot, ctx):
	mock_bot.draft_state.is_draft_started.return_value = True
	mock_bot.draft_state.can_draft.return_value = True
	cog = FantasyCog(mock_bot)
	await cog.draft.callback(cog, ctx, "NonexistentPlayer")
	sent = ctx.send.call_args[0][0]
	assert "No player was found" in sent


async def test_draft_player_already_drafted(mock_bot, ctx, engine):
	with SASession(engine) as s:
		team = db.Team(name="ProTeam", abbrev="PRO", region="na")
		s.add(team)
		s.flush()
		player = db.Player(name="StarPlayer", team_id=team.id)
		s.add(player)
		s.flush()
		ft = db.FantasyTeam(name="OtherFantasyTeam", abbrev="OFT")
		s.add(ft)
		s.flush()
		s.add(db.FantasyPlayer(player_id=player.id, fantasy_team_id=ft.id, position=1))
		s.commit()

	mock_bot.draft_state.is_draft_started.return_value = True
	mock_bot.draft_state.can_draft.return_value = True
	cog = FantasyCog(mock_bot)
	await cog.draft.callback(cog, ctx, "StarPlayer")
	sent = ctx.send.call_args[0][0]
	assert "already been drafted" in sent


# ── FantasyCog.standings() ────────────────────────────────────────────────────

async def test_standings_empty(mock_bot, ctx):
	cog = FantasyCog(mock_bot)
	await cog.standings.callback(cog, ctx)
	ctx.send.assert_awaited_once()
	assert "Standings" in ctx.send.call_args[0][0]


async def test_standings_shows_team(mock_bot, ctx, engine):
	with SASession(engine) as s:
		s.add(db.FantasyTeam(name="MyTeam", abbrev="MYT"))
		s.commit()

	cog = FantasyCog(mock_bot)
	await cog.standings.callback(cog, ctx)
	sent = ctx.send.call_args[0][0]
	assert "MYT" in sent
	assert "MyTeam" in sent
