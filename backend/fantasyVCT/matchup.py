"""
matchup.py — schedule generation and weekly score computation for H2H matchups.
No Discord coupling; pure logic.
"""
import fantasyVCT.database as db
from fantasyVCT.scoring import PointCalculator
from fantasyVCT.utils import POSITIONS

from sqlalchemy import select
from sqlalchemy.orm import Session
from collections import defaultdict


def generate_schedule(
    team_ids: list[int], num_weeks: int, round_offset: int = 0
) -> list[list[tuple[int, int | None, int | None]]]:
    """Generate a round-robin matchup schedule.

    Returns a list of length num_weeks. Each entry is a list of
    (home_id, away_id, ghost_mirror_id) triples for that week.
    away_id is None for ghost matchups (odd team count).
    ghost_mirror_id is the real team whose score the ghost mirrors (None for non-ghost).

    Uses the circle/polygon algorithm for round-robin scheduling.
    If num_weeks > num_rounds, the schedule repeats from the beginning.

    Args:
        team_ids: list of fantasy_team ids to schedule
        num_weeks: total number of weeks to schedule
        round_offset: which round index to start from (for stage continuation)

    Returns:
        list[list[tuple[int, int | None, int | None]]]:
            schedule[week_index] = [(home, away, ghost_mirror_id), ...]
    """
    if len(team_ids) < 2:
        raise ValueError("Need at least 2 teams to generate a schedule")

    teams = list(team_ids)

    # Pad to even count with a ghost (None) for bye/ghost matchups
    if len(teams) % 2 != 0:
        teams.append(None)  # ghost slot

    n = len(teams)
    num_rounds = n - 1  # one full round-robin cycle

    # Generate one full cycle of round-robin rounds
    rounds = []
    rotation = teams[1:]  # first team is fixed; rotate the rest

    for round_idx in range(num_rounds):
        raw_pairs = []
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
            raw_pairs.append((home, away))

        # For ghost pairs, mirror the first real team in the round
        ghost_mirror = next((h for h, a in raw_pairs if a is not None), None)
        pairs = [
            (home, away, ghost_mirror if away is None else None)
            for home, away in raw_pairs
        ]
        rounds.append(pairs)

        # Rotate: move last element of rotation to front
        rotation = [rotation[-1]] + rotation[:-1]

    # Build the full schedule, repeating the cycle if needed, starting at round_offset
    schedule = []
    for week_idx in range(num_weeks):
        schedule.append(rounds[(round_offset + week_idx) % num_rounds])

    return schedule


def get_season_chain(season: "db.Season") -> list["db.Season"]:
    """Walk previous_season_id links back to the root stage.

    Returns list from oldest→newest season.

    Args:
        season: the current (latest) Season object

    Returns:
        list[Season]: [root, ..., season]
    """
    chain = [season]
    current = season
    while current.previous_season is not None:
        current = current.previous_season
        chain.append(current)
    chain.reverse()
    return chain


def compute_round_offset(total_prev_weeks: int, num_teams: int) -> int:
    """Compute which round to start from for stage continuation.

    Pads odd team counts to even before computing cycle length.

    Args:
        total_prev_weeks: total weeks played across all previous stages
        num_teams: number of fantasy teams

    Returns:
        int: starting round index for the new stage
    """
    padded = num_teams if num_teams % 2 == 0 else num_teams + 1
    num_rounds = padded - 1
    return total_prev_weeks % num_rounds


def compute_weekly_score(fantasy_team_id: int, week_id: int, session: Session) -> float:
    """Compute a fantasy team's score for a given week.

    For each active roster player (positions 0–5), computes base + role bonus for
    each result tagged to week_id, sorts descending, and takes the top 2 maps.
    Weekly score is the sum of each player's top-2 map totals.

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

    # Group results by player
    player_results = defaultdict(list)
    for result in results:
        player_results[result.player_id].append(result)

    total = 0.0
    for player_id, maps in player_results.items():
        role = POSITIONS[active_roster[player_id]]
        map_totals = sorted(
            (PointCalculator.score(r) + PointCalculator.role_bonus(r, role) for r in maps),
            reverse=True
        )
        total += sum(map_totals[:2])

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
