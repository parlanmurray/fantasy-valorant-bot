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
	ConfigCog, FantasyCog, StatsCog, Category, add_spaces, POSITIONS, _optimal_score,
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
	await cog.register.callback(cog, ctx, "NEW", "New Team")
	ctx.send.assert_awaited_once_with("You have already registered a team.")


async def test_register_name_taken(mock_bot, ctx, engine):
	with SASession(engine) as s:
		s.add(db.FantasyTeam(name="Team Alpha", abbrev="OTH"))
		s.commit()

	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "TST", "Team Alpha")
	sent = ctx.send.call_args[0][0]
	assert "Team Alpha" in sent
	assert "taken" in sent


async def test_register_abbrev_taken(mock_bot, ctx, engine):
	with SASession(engine) as s:
		s.add(db.FantasyTeam(name="Other Team", abbrev="TST"))
		s.commit()

	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "TST", "My Team")
	sent = ctx.send.call_args[0][0]
	assert "TST" in sent
	assert "taken" in sent


async def test_register_success(mock_bot, ctx):
	cog = ConfigCog(mock_bot)
	await cog.register.callback(cog, ctx, "TST", "Test Team")
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


# ── _optimal_score ────────────────────────────────────────────────────────────

def _make_fp(player_id, team_id):
	"""Build a mock FantasyPlayer with a player stub."""
	fp = MagicMock()
	fp.player.id = player_id
	fp.player.team_id = team_id
	return fp


def _make_fteam(fps):
	ft = MagicMock()
	ft.fantasyplayers = fps
	return ft


def _make_cache(scores: dict):
	cache = MagicMock()
	cache.retrieve_total.side_effect = lambda pid: scores.get(pid, 0)
	return cache


class TestOptimalScore:
	def test_empty_team(self):
		ft = _make_fteam([])
		assert _optimal_score(ft, _make_cache({})) == 0.0

	def test_all_distinct_teams_best_captain(self):
		# 6 players, each on different pro teams; best scorer should become captain
		fps = [_make_fp(i, i) for i in range(6)]
		scores = {0: 100, 1: 80, 2: 60, 3: 40, 4: 20, 5: 10}
		cache = _make_cache(scores)
		result = _optimal_score(_make_fteam(fps), cache)
		# captain=100×1.2 + 80+60+40+20+10 = 120+210 = 330
		assert result == 330.0

	def test_suboptimal_captain_triggers_asterisk(self):
		# 6 players distinct teams; captain is worst scorer → optimal > actual
		fps = [_make_fp(i, i) for i in range(6)]
		scores = {0: 10, 1: 80, 2: 60, 3: 40, 4: 20, 5: 100}
		# optimal: captain=player5(100) → 100×1.2 + 80+60+40+20+10 = 120+210 = 330
		cache = _make_cache(scores)
		result = _optimal_score(_make_fteam(fps), cache)
		assert result == 330.0

	def test_captain_can_share_team_with_active(self):
		# Captain (pos 0) is exempt from team restriction; captain and one active can share team 99
		fps = [
			_make_fp(0, 99),  # score 100, team 99 → captain
			_make_fp(1, 99),  # score 90, team 99 → allowed as active (captain exempt)
			_make_fp(2, 2),   # score 80
			_make_fp(3, 3),   # score 70
			_make_fp(4, 4),   # score 60
			_make_fp(5, 5),   # score 50
			_make_fp(6, 6),   # score 40
		]
		scores = {0: 100, 1: 90, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40}
		cache = _make_cache(scores)
		# captain=0(100,T99), active: 1(90,T99)✓, 2(80,T2)✓, 3(70,T3)✓, 4(60,T4)✓, 5(50,T5)✓
		# total = 100×1.2 + 90+80+70+60+50 = 120+350 = 470
		result = _optimal_score(_make_fteam(fps), cache)
		assert result == 470.0

	def test_two_same_team_active_not_both_chosen(self):
		# Players 4 and 5 share team 99; player 0 dominates as captain (large gap)
		# so both T99 players compete for active slots — only the better one is chosen
		fps = [
			_make_fp(0, 1),   # score 1000, T1 — dominant captain
			_make_fp(1, 2),   # score 80
			_make_fp(2, 3),   # score 70
			_make_fp(3, 4),   # score 60
			_make_fp(4, 99),  # score 50, T99
			_make_fp(5, 99),  # score 40, T99 — same team, cannot both be active
			_make_fp(6, 5),   # score 10
		]
		scores = {0: 1000, 1: 80, 2: 70, 3: 60, 4: 50, 5: 40, 6: 10}
		cache = _make_cache(scores)
		# captain=0(1000): active=[80,70,60,50(T99),skip 40(T99),10]=[80,70,60,50,10]=270
		# total = 1000×1.2 + 270 = 1200+270 = 1470
		result = _optimal_score(_make_fteam(fps), cache)
		assert result == 1470.0
