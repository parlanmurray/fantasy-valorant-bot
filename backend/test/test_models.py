"""P2 — ORM model tests.
Uses SQLite in-memory; no live DB or Docker required.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from fantasyVCT.database import (
    Base, Team, Player, Event, Result, FantasyTeam, User, Position,
    FantasyPlayer, Map, Match,
)


@pytest.fixture(scope="module")
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
def session(engine):
    with Session(engine) as s:
        yield s
        s.rollback()


# ── Non-mapped helpers ───────────────────────────────────────────────────────

class TestTeamGetPlayer:
    def _team(self, names):
        t = Team(name="T1", abbrev="T1X", region="kr")
        t.players = [Player(name=n) for n in names]
        return t

    def test_found(self):
        t = self._team(["TenZ", "SicK"])
        assert t.get_player("TenZ").name == "TenZ"

    def test_not_found_returns_none(self):
        t = self._team(["TenZ"])
        assert t.get_player("aspas") is None

    def test_empty_roster(self):
        t = Team(name="Empty", abbrev="X", region="na")
        t.players = []
        assert t.get_player("TenZ") is None


class TestMatchGetMap:
    def test_found(self):
        m = Match(match_id=1)
        mp = Map(game_id=7)
        m.maps.append(mp)
        assert m.get_map(7) is mp

    def test_not_found_returns_none(self):
        m = Match(match_id=1)
        assert m.get_map(99) is None

    def test_multiple_maps_returns_correct_one(self):
        m = Match(match_id=1)
        m.maps = [Map(game_id=i) for i in range(3)]
        assert m.get_map(2).game_id == 2


# ── ORM CRUD ─────────────────────────────────────────────────────────────────

class TestTeam:
    def test_create(self, session):
        t = Team(name="Sentinels", abbrev="SEN", region="na")
        session.add(t)
        session.flush()
        assert t.id is not None

    def test_repr(self):
        t = Team(id=1, name="Sentinels", abbrev="SEN", region="na")
        assert "Sentinels" in repr(t)


class TestPlayer:
    def test_create_without_team(self, session):
        p = Player(name="solo_player")
        session.add(p)
        session.flush()
        assert p.id is not None
        assert p.team_id is None

    def test_create_with_team(self, session):
        t = Team(name="100T", abbrev="100T", region="na")
        session.add(t)
        session.flush()
        p = Player(name="bang", team_id=t.id)
        session.add(p)
        session.flush()
        assert p.team_id == t.id

    def test_repr(self):
        p = Player(id=5, name="TenZ", team_id=1)
        assert "TenZ" in repr(p)


class TestEvent:
    def test_create(self, session):
        e = Event(name="VCT Masters 2026")
        session.add(e)
        session.flush()
        assert e.id is not None

    def test_repr(self):
        e = Event(id=1, name="VCT")
        assert "VCT" in repr(e)


class TestResult:
    def _result_kwargs(self, player_id, event_id):
        return dict(
            map="Ascent", game_id=1, match_id=10, player_id=player_id,
            event_id=event_id,
            player_acs=200.0, player_kills=15, player_deaths=8, player_assists=3,
            player_2k=2, player_3k=1, player_4k=0, player_5k=0,
            player_clutch_v2=1, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0,
            agent="Jett",
        )

    def test_create(self, session):
        e = Event(name="TestEvent")
        p = Player(name="shooter")
        session.add_all([e, p])
        session.flush()
        r = Result(**self._result_kwargs(p.id, e.id))
        session.add(r)
        session.flush()
        assert r.id is not None

    def test_repr(self):
        r = Result(id=1, map="Bind", game_id=2, match_id=5, player_id=3)
        assert "Bind" in repr(r)


class TestFantasyTeam:
    def test_create(self, session):
        ft = FantasyTeam(name="My Fantasy Team", abbrev="MFT")
        session.add(ft)
        session.flush()
        assert ft.id is not None

    def test_repr(self):
        ft = FantasyTeam(id=1, name="Team Alpha", abbrev="TA")
        assert "Team Alpha" in repr(ft)


class TestUser:
    def test_create_standalone(self, session):
        u = User(discord_id="123456789012345678")
        session.add(u)
        session.flush()
        assert u.discord_id == "123456789012345678"

    def test_create_with_fantasyteam(self, session):
        ft = FantasyTeam(name="UsrFT", abbrev="UFT")
        session.add(ft)
        session.flush()
        u = User(discord_id="987654321098765432", fantasy_team_id=ft.id)
        session.add(u)
        session.flush()
        assert u.fantasy_team_id == ft.id

    def test_repr(self):
        u = User(discord_id="111", fantasy_team_id=None)
        assert "111" in repr(u)


class TestPosition:
    def test_create(self, session):
        pos = Position(id=100, position="captain_test")
        session.add(pos)
        session.flush()
        assert pos.id == 100

    def test_repr(self):
        pos = Position(id=1, position="player1")
        assert "player1" in repr(pos)


class TestFantasyPlayer:
    def test_create(self, session):
        ft = FantasyTeam(name="FP_FT", abbrev="FPT")
        p = Player(name="fp_player")
        pos = Position(id=200, position="fp_captain")
        session.add_all([ft, p, pos])
        session.flush()
        fp = FantasyPlayer(player_id=p.id, fantasy_team_id=ft.id, position=200)
        session.add(fp)
        session.flush()
        assert fp.id is not None

    def test_repr(self):
        fp = FantasyPlayer(id=1, player_id=2, fantasy_team_id=3, position=0)
        assert "1" in repr(fp)


# ── Relationships ─────────────────────────────────────────────────────────────

class TestRelationships:
    def test_team_players(self, session):
        t = Team(name="FaZe", abbrev="FAZ", region="eu")
        session.add(t)
        session.flush()
        p1 = Player(name="Boaster", team_id=t.id)
        p2 = Player(name="Derke", team_id=t.id)
        session.add_all([p1, p2])
        session.flush()
        session.refresh(t)
        assert len(t.players) == 2

    def test_player_results(self, session):
        e = Event(name="RelEvent")
        p = Player(name="star_player")
        session.add_all([e, p])
        session.flush()
        r = Result(
            map="Icebox", game_id=1, match_id=20, player_id=p.id,
            event_id=e.id,
            player_acs=0, player_kills=0, player_deaths=0, player_assists=0,
            player_2k=0, player_3k=0, player_4k=0, player_5k=0,
            player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0,
            player_clutch_v5=0, agent="Sage",
        )
        session.add(r)
        session.flush()
        session.refresh(p)
        assert len(p.results) == 1


# ── FK violation ─────────────────────────────────────────────────────────────

class TestFKViolation:
    def test_player_invalid_team_id_raises(self, session):
        p = Player(name="orphan", team_id=99999)
        session.add(p)
        with pytest.raises(IntegrityError):
            session.flush()
