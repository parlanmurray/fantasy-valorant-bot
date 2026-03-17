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


# ── StatsCog.rankplayers() ────────────────────────────────────────────────────

async def test_rankplayers_picks_up_new_games_after_stale_total(mock_bot, ctx, engine):
	# Regression: get_fantasy_points used `if not total` guard, so new games
	# added after a stale total was cached were never fetched from the DB.
	from fantasyVCT.scoring import Cache
	from fantasyVCT.database import Result

	def _result(pid, eid, game_id, kills):
		return Result(player_id=pid, game_id=game_id, match_id="m1",
			map="Haven", event_id=eid, agent="Jett",
			player_acs=0, player_kills=kills, player_deaths=0, player_assists=0,
			player_2k=0, player_3k=0, player_4k=0, player_5k=0,
			player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0)

	with SASession(engine) as s:
		event = db.Event(name="TestEvent")
		team = db.Team(name="ProTeam", abbrev="PRO", region="na")
		s.add_all([event, team])
		s.flush()
		player = db.Player(name="TestPlayer", team_id=team.id)
		s.add(player)
		s.flush()
		s.add(_result(player.id, event.id, game_id=1, kills=10))
		s.add(_result(player.id, event.id, game_id=2, kills=5))
		s.commit()
		pid, eid = player.id, event.id

	# Simulate stale cache state: old games cached, total rebuilt to stale value
	cache = Cache()
	cache.store(pid, 1, 20.0)
	cache.store(pid, 2, 10.0)
	cache.retrieve_total(pid)   # caches 30.0
	cache.invalidate()
	cache.retrieve_total(pid)   # rebuilds stale 30.0 from old entries

	# New game added to DB (simulating an upload)
	with SASession(engine) as s:
		s.add(_result(pid, eid, game_id=3, kills=20))
		s.commit()

	mock_bot.cache = cache
	cog = StatsCog(mock_bot)
	await cog.rankplayers.callback(cog, ctx)
	sent = "".join(call[0][0] for call in ctx.send.call_args_list)
	# game 3: 20 kills * 1.5 = 30.0; total should be 20+10+30 = 60.0, not stale 30.0
	assert "60.0" in sent



# ── Unicode / non-ASCII handling ──────────────────────────────────────────────

def _seed_unicode_player(engine):
	"""Insert a BBL team with Rosé as a player. Returns (team_id, player_id)."""
	with SASession(engine) as s:
		team = db.Team(name="BBL Esports", abbrev="BBL", region="EMEA")
		s.add(team)
		s.flush()
		player = db.Player(name="Rosé", team_id=team.id)
		s.add(player)
		s.commit()
		return team.id, player.id


class TestUnicodeHandling:
	"""Regression tests: non-ASCII player names must survive the full
	store → retrieve → display round-trip without garbling."""

	async def test_freeagents_displays_non_ascii_name(self, mock_bot, ctx, engine):
		"""Rosé appears correctly in !freeagents output when undrafted."""
		_seed_unicode_player(engine)
		mock_bot.cache.retrieve_total.return_value = 0
		mock_bot.cache.retrieve.return_value = None

		cog = FantasyCog(mock_bot)
		await cog.freeagents.callback(cog, ctx)

		sent = "".join(call[0][0] for call in ctx.send.call_args_list)
		assert "Rosé" in sent
		assert "RosÃ©" not in sent

	async def test_freeagents_does_not_display_garbled_encoding(self, mock_bot, ctx, engine):
		"""The double-encoded form RosÃ© must never appear in output."""
		_seed_unicode_player(engine)
		mock_bot.cache.retrieve_total.return_value = 0
		mock_bot.cache.retrieve.return_value = None

		cog = FantasyCog(mock_bot)
		await cog.freeagents.callback(cog, ctx)

		sent = "".join(call[0][0] for call in ctx.send.call_args_list)
		assert "RosÃ©" not in sent

	async def test_info_finds_player_by_non_ascii_name(self, mock_bot, ctx, engine):
		"""!info Rosé resolves the player and displays their name correctly."""
		_seed_unicode_player(engine)
		mock_bot.cache.retrieve_total.return_value = 0
		mock_bot.cache.retrieve.return_value = None

		cog = StatsCog(mock_bot)
		await cog.info.callback(cog, ctx, "Rosé")

		sent = "".join(call[0][0] for call in ctx.send.call_args_list)
		assert "Rosé" in sent
		assert "not found" not in sent

	async def test_info_not_found_for_garbled_name(self, mock_bot, ctx, engine):
		"""!info RosÃ© (garbled) must not match the correctly stored player."""
		_seed_unicode_player(engine)

		cog = StatsCog(mock_bot)
		await cog.info.callback(cog, ctx, "RosÃ©")

		sent = ctx.send.call_args[0][0]
		assert "not found" in sent

	async def test_draft_with_non_ascii_player_name(self, mock_bot, ctx, engine):
		"""!draft Rosé picks up the player correctly when it is their turn."""
		_seed_unicode_player(engine)

		with SASession(engine) as s:
			ft = db.FantasyTeam(name="TestTeam", abbrev="TST")
			s.add(ft)
			s.flush()
			s.add(db.User(discord_id=AUTHOR_ID, fantasy_team_id=ft.id))
			s.commit()

		mock_bot.draft_state.is_draft_started.return_value = True
		mock_bot.draft_state.can_draft.return_value = True
		mock_bot.draft_state.is_draft_complete.return_value = False
		mock_bot.draft_state.next.return_value = None
		mock_bot.sub_slots = 2

		cog = FantasyCog(mock_bot)
		await cog.draft.callback(cog, ctx, "Rosé")

		sent = "".join(call[0][0] for call in ctx.send.call_args_list)
		# draft succeeded: completion message sent, no error about player not found
		assert "Initial draft is complete!" in sent
		assert "No player was found" not in sent


# ── Role bonus integration ─────────────────────────────────────────────────────

class TestRoleBonusIntegration:
	"""Integration: role assignment in DB → score compute → !standings output.

	Verifies the full vertical slice: role stored as position int in DB,
	looked up via POSITIONS dict, passed to role_bonus(), reflected in output.
	"""

	def _seed(self, engine, position, kills=0, fk=0, assists=0, deaths=0, team_won=None):
		with SASession(engine) as s:
			team = db.Team(name="ProTeam", abbrev="PRO", region="na")
			s.add(team)
			s.flush()
			player = db.Player(name="TestPlayer", team_id=team.id)
			s.add(player)
			s.flush()
			ft = db.FantasyTeam(name="MyTeam", abbrev="MYT")
			s.add(ft)
			s.flush()
			s.add(db.User(discord_id=AUTHOR_ID, fantasy_team_id=ft.id))
			s.add(db.FantasyPlayer(player_id=player.id, fantasy_team_id=ft.id, position=position))
			s.add(db.Result(
				player_id=player.id, game_id=1, match_id=1,
				map="Haven", event_id=1, agent="Jett",
				player_acs=0, player_kills=kills, player_deaths=deaths,
				player_assists=assists,
				player_2k=0, player_3k=0, player_4k=0, player_5k=0,
				player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0,
				player_fk=fk, team_won=team_won,
			))
			s.commit()

	async def test_duelist_fk_bonus_in_standings(self, mock_bot, ctx, engine):
		"""Duelist FK role bonus is included in standings total.

		kills=10 → base 15.0; fk=5 → base 5.0; total base 20.0
		Duelist bonus: fk=5 × 2.0 = 10.0 → standings total 30.0
		"""
		from fantasyVCT.scoring import Cache
		self._seed(engine, position=1, kills=10, fk=5)
		mock_bot.cache = Cache()

		cog = FantasyCog(mock_bot)
		await cog.standings.callback(cog, ctx)

		assert "30.0" in ctx.send.call_args[0][0]

	async def test_igl_win_bonus_in_standings(self, mock_bot, ctx, engine):
		"""IGL win bonus (+8.5) is included in standings total.

		kills=5 → base 7.5; IGL win → +8.5; standings total 16.0
		"""
		from fantasyVCT.scoring import Cache
		self._seed(engine, position=0, kills=5, team_won=True)
		mock_bot.cache = Cache()

		cog = FantasyCog(mock_bot)
		await cog.standings.callback(cog, ctx)

		assert "16.0" in ctx.send.call_args[0][0]

	async def test_flex_earns_no_role_bonus_in_standings(self, mock_bot, ctx, engine):
		"""Flex (position 5) earns no role bonus despite having FKs.

		kills=10 → base 15.0; fk=5 → base 5.0; Flex bonus = 0; standings total 20.0
		"""
		from fantasyVCT.scoring import Cache
		self._seed(engine, position=5, kills=10, fk=5)
		mock_bot.cache = Cache()

		cog = FantasyCog(mock_bot)
		await cog.standings.callback(cog, ctx)

		assert "20.0" in ctx.send.call_args[0][0]
