"""
matchup.py — schedule generation and weekly score computation for H2H matchups.
No Discord coupling; pure logic.
"""
import fantasyVCT.database as db
from fantasyVCT.scoring import PointCalculator

from sqlalchemy import select
from sqlalchemy.orm import Session


def generate_schedule(team_ids: list[int], num_weeks: int) -> list[list[tuple[int, int | None]]]:
    """Generate a round-robin matchup schedule.

    Returns a list of length num_weeks. Each entry is a list of (home_id, away_id) pairs
    for that week. away_id is None for ghost matchups when team count is odd.

    Uses the circle/polygon algorithm for round-robin scheduling.
    If num_weeks > num_rounds, the schedule repeats from the beginning.

    Args:
        team_ids: list of fantasy_team ids to schedule
        num_weeks: total number of weeks to schedule

    Returns:
        list[list[tuple[int, int | None]]]: schedule[week_index] = [(home, away), ...]
    """
    if len(team_ids) < 2:
        raise ValueError("Need at least 2 teams to generate a schedule")

    teams = list(team_ids)
    ghost = None

    # Pad to even count with a ghost (None) for bye/ghost matchups
    if len(teams) % 2 != 0:
        teams.append(None)  # ghost slot
        ghost = None

    n = len(teams)
    num_rounds = n - 1  # one full round-robin cycle

    # Generate one full cycle of round-robin rounds
    rounds = []
    rotation = teams[1:]  # first team is fixed; rotate the rest

    for round_idx in range(num_rounds):
        pairs = []
        fixed = teams[0]
        round_teams = [fixed] + rotation

        for i in range(n // 2):
            home = round_teams[i]
            away = round_teams[n - 1 - i]
            # Skip pure-ghost vs ghost (shouldn't happen, but guard anyway)
            if home is None and away is None:
                continue
            # Always put ghost in away slot
            if home is None:
                home, away = away, home
            pairs.append((home, away))
        rounds.append(pairs)

        # Rotate: move last element of rotation to front
        rotation = [rotation[-1]] + rotation[:-1]

    # Build the full schedule, repeating the cycle if needed
    schedule = []
    for week_idx in range(num_weeks):
        schedule.append(rounds[week_idx % num_rounds])

    return schedule


def compute_weekly_score(fantasy_team_id: int, week_id: int, session: Session) -> float:
    """Compute a fantasy team's score for a given week.

    Sums PointCalculator.score() for all results tagged to week_id whose
    player is on the team's active roster (positions 0–5). Captain (position 0)
    gets the 1.2× multiplier.

    Args:
        fantasy_team_id: id of the FantasyTeam
        week_id: id of the Week
        session: active SQLAlchemy session

    Returns:
        float: total weekly fantasy points
    """
    fteam = session.get(db.FantasyTeam, fantasy_team_id)
    if not fteam:
        return 0.0

    # Collect active roster player ids and their positions
    active_roster = {
        fp.player_id: fp.position
        for fp in fteam.fantasyplayers
        if fp.position < 6
    }
    if not active_roster:
        return 0.0

    results = session.scalars(
        select(db.Result).where(
            db.Result.week_id == week_id,
            db.Result.player_id.in_(active_roster.keys())
        )
    ).all()

    total = 0.0
    for result in results:
        pts = PointCalculator.score(result)
        if active_roster[result.player_id] == 0:
            pts *= 1.2
        total += pts

    return round(total, 1)


def derive_record(matchups: list[db.Matchup], fantasy_team_id: int) -> tuple[int, int, int]:
    """Derive W/L/T record for a team from a list of closed matchups.

    A matchup is considered closed (scorable) when home_score > 0 or away_score > 0.
    Ghost matchups (away_team_id = None) are counted normally against the ghost score.

    Args:
        matchups: list of Matchup objects involving this team
        fantasy_team_id: the team whose record to compute

    Returns:
        tuple[int, int, int]: (wins, losses, ties)
    """
    wins = losses = ties = 0
    for m in matchups:
        if m.home_team_id == fantasy_team_id:
            my_score, opp_score = m.home_score, m.away_score
        else:
            my_score, opp_score = m.away_score, m.home_score

        if my_score > opp_score:
            wins += 1
        elif my_score < opp_score:
            losses += 1
        else:
            ties += 1

    return wins, losses, ties
