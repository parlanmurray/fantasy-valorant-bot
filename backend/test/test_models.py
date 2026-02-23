"""Unit 1: smoke tests for Season, Week, Matchup models and Result.week_id."""
from fantasyVCT.database import Season, Week, Matchup, Result


def test_season_instantiate():
    s = Season(name="VCT 2025 Americas Stage 1", event_url="https://vlr.gg/event/2347", num_weeks=5, is_active=True)
    assert s.name == "VCT 2025 Americas Stage 1"
    assert s.num_weeks == 5
    assert s.is_active is True


def test_week_instantiate():
    w = Week(season_id=1, week_number=3)
    assert w.week_number == 3
    assert w.season_id == 1


def test_matchup_instantiate():
    m = Matchup(week_id=1, home_team_id=1, away_team_id=2, home_score=0.0, away_score=0.0)
    assert m.week_id == 1
    assert m.home_team_id == 1
    assert m.away_team_id == 2
    assert m.home_score == 0.0
    assert m.away_score == 0.0


def test_matchup_ghost_away_null():
    """away_team_id can be NULL for ghost matchups."""
    m = Matchup(week_id=1, home_team_id=1, away_team_id=None)
    assert m.away_team_id is None


def test_result_has_week_id():
    r = Result()
    assert hasattr(r, 'week_id')
    assert r.week_id is None
