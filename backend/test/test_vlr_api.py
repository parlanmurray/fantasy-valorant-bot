"""P4 — FetchCog tests: upload deduplication and HTTP error handling.
No live network or Discord token required; uses SQLite in-memory + mocks.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from contextlib import contextmanager

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session as SASession

import fantasyVCT.database as db
from fantasyVCT.database import Base
from fantasyVCT.vlr_api import FetchCog


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
	yield eng
	eng.dispose()


@pytest.fixture
def mock_bot(engine):
	bot = MagicMock()
	bot.cache = MagicMock()

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


# ── upload() ─────────────────────────────────────────────────────────────────

async def test_upload_invalid_id(mock_bot, ctx):
	cog = FetchCog(mock_bot)
	await cog.upload.callback(cog, ctx, "not-a-number")
	ctx.send.assert_awaited_once_with("Not a valid vlr match number.")


async def test_upload_invalid_id_float(mock_bot, ctx):
	cog = FetchCog(mock_bot)
	await cog.upload.callback(cog, ctx, "1.5")
	ctx.send.assert_awaited_once_with("Not a valid vlr match number.")


async def test_upload_duplicate(mock_bot, ctx, engine):
	with SASession(engine) as s:
		player = db.Player(name="dup_player")
		s.add(player)
		s.flush()
		s.add(db.Result(
			map="Ascent", game_id=1, match_id=12345, event_id=1,
			player_id=player.id,
			player_acs=200.0, player_kills=10, player_deaths=5, player_assists=2,
			player_2k=0, player_3k=0, player_4k=0, player_5k=0,
			player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0,
			agent="Jett",
		))
		s.commit()

	cog = FetchCog(mock_bot)
	await cog.upload.callback(cog, ctx, "12345")
	ctx.send.assert_awaited_once_with("This match has already been uploaded.")


async def test_upload_success_inserts_results(mock_bot, ctx, engine):
	"""Valid new match with existing teams/players: results inserted, cache invalidated.
	Note: upload() doesn't set Team.region (pre-existing omission), so teams must be
	pre-seeded to avoid the NOT NULL constraint on that column.
	"""
	with SASession(engine) as s:
		t_a = db.Team(name="TeamA", abbrev="TMA", region="na")
		t_b = db.Team(name="TeamB", abbrev="TMB", region="eu")
		s.add_all([t_a, t_b])
		s.flush()
		p_a = db.Player(name="PlayerA", team_id=t_a.id)
		p_b = db.Player(name="PlayerB", team_id=t_b.id)
		s.add_all([p_a, p_b])
		s.commit()

	def _result(game_id):
		return db.Result(
			map="Bind", game_id=game_id, match_id=99999, event_id=1,
			player_acs=150.0, player_kills=12, player_deaths=7, player_assists=4,
			player_2k=1, player_3k=0, player_4k=0, player_5k=0,
			player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0,
			agent="Sage",
		)

	def _scraped_team(name, abbrev, player_name, game_id):
		p = MagicMock()
		p.name = player_name
		p.results = [_result(game_id)]
		t = MagicMock()
		t.name = name
		t.abbrev = abbrev
		t.players = [p]
		return t

	map_mock = MagicMock()
	map_mock.team1 = _scraped_team("TeamA", "TMA", "PlayerA", 99001)
	map_mock.team2 = _scraped_team("TeamB", "TMB", "PlayerB", 99002)
	match_mock = MagicMock()
	match_mock.maps = [map_mock]
	mock_bot.scraper.parse_match.return_value = match_mock

	cog = FetchCog(mock_bot)
	await cog.upload.callback(cog, ctx, "99999")

	with SASession(engine) as s:
		results = list(s.scalars(select(db.Result).filter_by(match_id=99999)))
		assert len(results) == 2

	mock_bot.cache.invalidate.assert_called_once()


# ── get_results() ─────────────────────────────────────────────────────────────

async def test_get_results_http_error(mock_bot):
	with patch("fantasyVCT.vlr_api.requests.get") as mock_get:
		mock_get.return_value.status_code = 503
		cog = FetchCog(mock_bot)
		await cog.get_results()
	mock_bot.db_manager.query_events_from_name.assert_not_called()


async def test_get_results_untracked_tournament(mock_bot):
	mock_bot.db_manager.query_events_from_name.return_value = None
	with patch("fantasyVCT.vlr_api.requests.get") as mock_get, \
	     patch("fantasyVCT.vlr_api.asyncio.sleep"):
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = {
			"data": {"segments": [
				{"tournament_name": "Unknown Event", "match_page": "12345/team-a-vs-team-b"}
			]}
		}
		cog = FetchCog(mock_bot)
		await cog.get_results()
	mock_bot.db_manager.query_results_all_from_match_id.assert_not_called()


async def test_get_results_duplicate_skipped(mock_bot):
	mock_bot.db_manager.query_events_from_name.return_value = (1, "VCT Masters")
	mock_bot.db_manager.query_results_all_from_match_id.return_value = [(1, "12345")]
	with patch("fantasyVCT.vlr_api.requests.get") as mock_get, \
	     patch("fantasyVCT.vlr_api.asyncio.sleep"):
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = {
			"data": {"segments": [
				{"tournament_name": "VCT Masters", "match_page": "12345/team-a-vs-team-b"}
			]}
		}
		cog = FetchCog(mock_bot)
		await cog.get_results()
	mock_bot.scraper.parse_match.assert_not_called()
