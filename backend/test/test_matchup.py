"""Tests for matchup.py — schedule generation, score computation, W/L/T derivation."""
import pytest
from unittest.mock import MagicMock

from fantasyVCT.matchup import generate_schedule, derive_record
import fantasyVCT.database as db


# ---------------------------------------------------------------------------
# generate_schedule
# ---------------------------------------------------------------------------

def test_schedule_even_teams():
    """4 teams → 3 rounds, each team plays exactly once per round."""
    teams = [1, 2, 3, 4]
    schedule = generate_schedule(teams, num_weeks=3)

    assert len(schedule) == 3
    for week_pairs in schedule:
        # 2 games per week for 4 teams
        assert len(week_pairs) == 2
        # No team appears twice in the same week
        seen = []
        for home, away in week_pairs:
            assert home not in seen
            assert away not in seen
            seen.extend([home, away])


def test_schedule_even_full_roundrobin():
    """4 teams: across 3 rounds every pair meets exactly once."""
    teams = [1, 2, 3, 4]
    schedule = generate_schedule(teams, num_weeks=3)

    pairs = set()
    for week_pairs in schedule:
        for home, away in week_pairs:
            pair = frozenset([home, away])
            assert pair not in pairs, f"Duplicate matchup: {pair}"
            pairs.add(pair)

    # C(4,2) = 6 unique pairs across 3 weeks
    assert len(pairs) == 6


def test_schedule_odd_teams():
    """3 teams → 3 rounds with one ghost slot (None) per round."""
    teams = [1, 2, 3]
    schedule = generate_schedule(teams, num_weeks=3)

    assert len(schedule) == 3
    for week_pairs in schedule:
        assert len(week_pairs) == 2  # 4 slots / 2 = 2 games (one has ghost)
        ghost_count = sum(1 for _, away in week_pairs if away is None)
        assert ghost_count == 1, "Exactly one ghost matchup per round with odd teams"


def test_schedule_repeat():
    """When num_weeks > num_rounds, schedule cycles from the beginning."""
    teams = [1, 2, 3, 4]
    # 3 rounds in one cycle; ask for 6 weeks → should repeat
    schedule = generate_schedule(teams, num_weeks=6)

    assert len(schedule) == 6
    # First 3 weeks == last 3 weeks
    assert schedule[0] == schedule[3]
    assert schedule[1] == schedule[4]
    assert schedule[2] == schedule[5]


def test_schedule_single_week():
    schedule = generate_schedule([1, 2], num_weeks=1)
    assert len(schedule) == 1
    assert len(schedule[0]) == 1
    assert frozenset(schedule[0][0]) == frozenset([1, 2])


def test_schedule_too_few_teams():
    with pytest.raises(ValueError):
        generate_schedule([1], num_weeks=1)


# ---------------------------------------------------------------------------
# derive_record
# ---------------------------------------------------------------------------

def _matchup(home_id, away_id, home_score, away_score):
    m = db.Matchup(
        week_id=1,
        home_team_id=home_id,
        away_team_id=away_id,
        home_score=home_score,
        away_score=away_score
    )
    return m


def test_derive_record_win():
    matchups = [_matchup(1, 2, 100.0, 80.0)]
    w, l, t = derive_record(matchups, fantasy_team_id=1)
    assert (w, l, t) == (1, 0, 0)


def test_derive_record_loss():
    matchups = [_matchup(1, 2, 60.0, 80.0)]
    w, l, t = derive_record(matchups, fantasy_team_id=1)
    assert (w, l, t) == (0, 1, 0)


def test_derive_record_tie():
    matchups = [_matchup(1, 2, 75.0, 75.0)]
    w, l, t = derive_record(matchups, fantasy_team_id=1)
    assert (w, l, t) == (0, 0, 1)


def test_derive_record_as_away_team():
    matchups = [_matchup(1, 2, 60.0, 80.0)]
    w, l, t = derive_record(matchups, fantasy_team_id=2)
    assert (w, l, t) == (1, 0, 0)


def test_derive_record_multi_week():
    matchups = [
        _matchup(1, 2, 100.0, 80.0),   # win
        _matchup(1, 3, 50.0, 90.0),    # loss
        _matchup(2, 1, 70.0, 70.0),    # tie (team 1 is away)
    ]
    w, l, t = derive_record(matchups, fantasy_team_id=1)
    assert (w, l, t) == (1, 1, 1)


def test_derive_record_sort_order():
    """Higher wins → ranked first."""
    team_a_matchups = [_matchup(1, 2, 100.0, 50.0), _matchup(1, 3, 90.0, 60.0)]
    team_b_matchups = [_matchup(1, 2, 100.0, 50.0), _matchup(3, 2, 80.0, 90.0)]

    wa, la, ta = derive_record(team_a_matchups, fantasy_team_id=1)
    wb, lb, tb = derive_record(team_b_matchups, fantasy_team_id=2)

    assert wa > wb  # team A has more wins
