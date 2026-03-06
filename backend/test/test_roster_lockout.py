"""Roster lockout tests: is_roster_locked helper, !drop/!draft/!set blocked when locked,
!lockroster sets lock, !closeweek unlocks."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import contextmanager

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session as SASession

import fantasyVCT.database as db
from fantasyVCT.database import Base
from fantasyVCT.fantasy_cog import FantasyCog
from fantasyVCT.matchup_cog import MatchupCog
from fantasyVCT.utils import is_roster_locked, POSITIONS


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
    bot.sub_slots = 2
    bot.num_rounds = 5
    bot.draft_state = MagicMock()

    @contextmanager
    def make_session():
        with SASession(engine) as s:
            yield s

    bot.db_manager.create_session = make_session
    return bot


@pytest.fixture
def ctx():
    c = MagicMock()
    c.send = AsyncMock()
    c.invoke = AsyncMock()
    c.message.author.id = AUTHOR_ID
    return c


def _seed_locked_season(engine):
    with SASession(engine) as s:
        season = db.Season(
            name="Test Season", event_url="https://vlr.gg/event/1",
            num_weeks=3, is_active=True, roster_locked=True
        )
        s.add(season)
        s.commit()
        return season.id


def _seed_unlocked_season(engine):
    with SASession(engine) as s:
        season = db.Season(
            name="Test Season", event_url="https://vlr.gg/event/1",
            num_weeks=3, is_active=True, roster_locked=False
        )
        s.add(season)
        s.commit()
        return season.id


def _seed_player_and_team(engine):
    with SASession(engine) as s:
        team = db.Team(name="T1", abbrev="T1", region="kr")
        s.add(team)
        s.flush()
        player = db.Player(name="TenZ", team_id=team.id)
        s.add(player)
        ft = db.FantasyTeam(name="MyTeam", abbrev="MT")
        s.add(ft)
        s.flush()
        s.add(db.User(discord_id=AUTHOR_ID, fantasy_team_id=ft.id))
        fp = db.FantasyPlayer(player_id=player.id, fantasy_team_id=ft.id, position=1)
        s.add(fp)
        s.commit()
        return player.id, ft.id


# ── is_roster_locked helper ───────────────────────────────────────────────────

def test_is_roster_locked_no_season(engine):
    with SASession(engine) as s:
        assert is_roster_locked(s) is False


def test_is_roster_locked_false_when_unlocked(engine):
    _seed_unlocked_season(engine)
    with SASession(engine) as s:
        assert is_roster_locked(s) is False


def test_is_roster_locked_true_when_locked(engine):
    _seed_locked_season(engine)
    with SASession(engine) as s:
        assert is_roster_locked(s) is True


# ── !drop blocked when locked ─────────────────────────────────────────────────

async def test_drop_blocked_when_locked(mock_bot, ctx, engine):
    _seed_locked_season(engine)
    _seed_player_and_team(engine)
    mock_bot.draft_state.is_draft_complete.return_value = True

    cog = FantasyCog(mock_bot)
    await cog.drop.callback(cog, ctx, "TenZ")

    sent = ctx.send.call_args[0][0]
    assert "locked" in sent


async def test_drop_allowed_when_unlocked(mock_bot, ctx, engine):
    _seed_unlocked_season(engine)
    _seed_player_and_team(engine)
    mock_bot.draft_state.is_draft_complete.return_value = True

    cog = FantasyCog(mock_bot)
    await cog.drop.callback(cog, ctx, "TenZ")

    sent = ctx.send.call_args[0][0]
    assert "free agent" in sent


# ── !draft (free agent add) blocked when locked ───────────────────────────────

async def test_draft_freeagent_blocked_when_locked(mock_bot, ctx, engine):
    _seed_locked_season(engine)
    mock_bot.draft_state.is_draft_started.return_value = True
    mock_bot.draft_state.can_draft.return_value = True
    mock_bot.draft_state.is_draft_complete.return_value = True

    cog = FantasyCog(mock_bot)
    await cog.draft.callback(cog, ctx, "TenZ")

    sent = ctx.send.call_args[0][0]
    assert "locked" in sent


async def test_draft_initial_pick_not_blocked_when_locked(mock_bot, ctx, engine):
    """Initial draft picks (draft not complete) bypass the roster lock."""
    _seed_locked_season(engine)
    mock_bot.draft_state.is_draft_started.return_value = True
    mock_bot.draft_state.can_draft.return_value = True
    mock_bot.draft_state.is_draft_complete.return_value = False

    with SASession(engine) as s:
        team = db.Team(name="NRG", abbrev="NRG", region="na")
        s.add(team)
        s.flush()
        player = db.Player(name="FNS", team_id=team.id)
        ft = db.FantasyTeam(name="DraftTeam", abbrev="DT")
        s.add_all([player, ft])
        s.flush()
        s.add(db.User(discord_id=AUTHOR_ID, fantasy_team_id=ft.id))
        s.commit()

    mock_bot.draft_state.next.return_value = None
    cog = FantasyCog(mock_bot)
    await cog.draft.callback(cog, ctx, "FNS")

    # Should not be blocked — no "locked" message
    sent = "".join(call[0][0] for call in ctx.send.call_args_list)
    assert "locked" not in sent


# ── !set blocked when locked ──────────────────────────────────────────────────

async def test_set_blocked_when_locked(mock_bot, ctx, engine):
    _seed_locked_season(engine)

    cog = FantasyCog(mock_bot)
    await cog.set.callback(cog, ctx, "TenZ", "captain")

    sent = ctx.send.call_args[0][0]
    assert "locked" in sent


async def test_set_allowed_when_unlocked(mock_bot, ctx, engine):
    _seed_unlocked_season(engine)
    _seed_player_and_team(engine)

    cog = FantasyCog(mock_bot)
    await cog.set.callback(cog, ctx, "TenZ", "captain")

    # Should proceed past lock check (may fail for other reasons, but not lockout)
    sent = "".join(call[0][0] for call in ctx.send.call_args_list)
    assert "locked" not in sent


# ── !closeweek unlocks rosters ────────────────────────────────────────────────

async def test_closeweek_unlocks_roster(mock_bot, ctx, engine):
    with SASession(engine) as s:
        season = db.Season(
            name="CS", event_url="https://vlr.gg/event/1",
            num_weeks=1, is_active=True, roster_locked=True
        )
        s.add(season)
        s.flush()
        week = db.Week(season_id=season.id, week_number=1)
        s.add(week)
        s.flush()
        ft1 = db.FantasyTeam(name="Team A", abbrev="TA")
        ft2 = db.FantasyTeam(name="Team B", abbrev="TB")
        s.add_all([ft1, ft2])
        s.flush()
        s.add(db.Matchup(week_id=week.id, home_team_id=ft1.id, away_team_id=ft2.id))
        s.commit()
        season_id = season.id

    cog = MatchupCog(mock_bot)
    await cog.closeweek.callback(cog, ctx, 1)

    with SASession(engine) as s:
        season = s.get(db.Season, season_id)
        assert season.roster_locked is False

    sent = ctx.send.call_args[0][0]
    assert "unlocked" in sent
