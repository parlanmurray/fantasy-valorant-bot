"""
matchup.py — schedule generation and weekly score computation for H2H matchups.
No Discord coupling; pure logic.
"""
import fantasyVCT.database as db
from fantasyVCT.scoring import PointCalculator
from fantasyVCT.utils import POSITIONS, build_opponent_map

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


def player_week_totals(player_id: int, position: int, week_id: int, session: Session) -> tuple[float, float, float]:
	"""Return (base, bonus, total) for a player's top-2 maps this week."""
	role = POSITIONS[position]
	results = session.scalars(
		select(db.Result).where(
			db.Result.week_id == week_id,
			db.Result.player_id == player_id,
		)
	).all()
	if not results:
		return 0.0, 0.0, 0.0
	map_scores = sorted(
		((PointCalculator.score(r), PointCalculator.role_bonus(r, role)) for r in results),
		key=lambda x: x[0] + x[1],
		reverse=True,
	)
	top2 = map_scores[:2]
	base  = round(sum(b for b, _ in top2), 1)
	bonus = round(sum(bn for _, bn in top2), 1)
	return base, bonus, round(base + bonus, 1)


def compute_weekly_score_snapshot(fantasy_team_id: int, week_id: int, session: Session) -> float:
	"""Compute a fantasy team's score using the roster snapshot for that week.

	Falls back to compute_weekly_score if no snapshot exists (e.g. pre-feature weeks).

	Args:
		fantasy_team_id: id of the FantasyTeam
		week_id: id of the Week
		session: active SQLAlchemy session

	Returns:
		float: total weekly fantasy points
	"""
	snapshots = session.scalars(
		select(db.RosterSnapshot).where(
			db.RosterSnapshot.fteam_id == fantasy_team_id,
			db.RosterSnapshot.week_id == week_id,
		)
	).all()

	if not snapshots:
		return compute_weekly_score(fantasy_team_id, week_id, session)

	active_roster = {
		s.player_id: s.position
		for s in snapshots
		if s.position < 6
	}
	if not active_roster:
		return 0.0

	results = session.scalars(
		select(db.Result).where(
			db.Result.week_id == week_id,
			db.Result.player_id.in_(active_roster.keys())
		)
	).all()

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


def get_roster_breakdown(fteam_id: int, week_id: int, session: Session) -> tuple[bool, list[dict]]:
	"""Return roster breakdown for display in !matchup.

	Uses roster snapshot if available; falls back to current fantasy_players.

	Args:
		fteam_id: id of the FantasyTeam
		week_id: id of the Week
		session: active SQLAlchemy session

	Returns:
		(has_snapshot, slots) where slots is a list of 10 dicts (positions 0–9):
		  position, role, player_name, base, bonus, is_active
	"""
	snapshots = session.scalars(
		select(db.RosterSnapshot).where(
			db.RosterSnapshot.fteam_id == fteam_id,
			db.RosterSnapshot.week_id == week_id,
		)
	).all()

	has_snapshot = bool(snapshots)

	if has_snapshot:
		# position -> player from snapshot
		pos_to_player: dict[int, db.Player] = {s.position: s.player for s in snapshots}
	else:
		# position -> player from current roster
		fps = session.scalars(
			select(db.FantasyPlayer).where(db.FantasyPlayer.fantasy_team_id == fteam_id)
		).all()
		pos_to_player = {fp.position: fp.player for fp in fps}

	slots = []
	for pos in range(10):
		player = pos_to_player.get(pos)
		is_active = pos < 6

		if player is None:
			player_name = None
			base, bonus = 0.0, 0.0
		else:
			pro_team = player.team.abbrev if player.team else ""
			player_name = f"{pro_team} {player.name}".strip() if pro_team else player.name
			if is_active:
				base, bonus, _ = player_week_totals(player.id, pos, week_id, session)
			else:
				base, bonus = 0.0, 0.0

		slots.append({
			"position":    pos,
			"role":        POSITIONS[pos],
			"player_name": player_name,
			"base":        base,
			"bonus":       bonus,
			"is_active":   is_active,
		})

	return has_snapshot, slots


def week_role_leaders(week_id: int, fteams: list, session: Session, n: int = 3) -> dict[str, list[dict]]:
	"""Return top-n performers per active role slot for the week.

	Args:
		week_id: Week.id to score against
		fteams: all FantasyTeam objects
		session: active SQLAlchemy session
		n: number of players to return per role

	Returns:
		dict keyed by role name ("IGL", "Duelist", ...) with list of
		{player, pro_team, fteam, base, bonus, total} dicts, sorted desc by total.
	"""
	role_buckets: dict[str, list[dict]] = defaultdict(list)

	for fteam in fteams:
		for fp in fteam.fantasyplayers:
			if fp.position >= 6:
				continue
			base, bonus, total = player_week_totals(fp.player_id, fp.position, week_id, session)
			if total == 0.0:
				continue
			role = POSITIONS[fp.position]
			pro_team = fp.player.team.abbrev if fp.player.team else "—"
			role_buckets[role].append({
				"player":    fp.player.name,
				"pro_team":  pro_team,
				"fteam":     fteam.abbrev,
				"base":      base,
				"bonus":     bonus,
				"total":     total,
			})

	return {
		role: sorted(role_buckets.get(role, []), key=lambda x: x["total"], reverse=True)[:n]
		for role in ["IGL", "Duelist", "Initiator", "Controller", "Sentinel", "Flex"]
	}


def week_top_base_scorers(week_id: int, fteams: list, session: Session, n: int = 5) -> list[dict]:
	"""Return top-n players by base score this week, including free agents.

	Args:
		week_id: Week.id to score against
		fteams: all FantasyTeam objects (used to identify drafted players)
		session: active SQLAlchemy session
		n: number of players to return

	Returns:
		list of {player, pro_team, fteam (None if free agent), base} dicts,
		sorted desc by base score.
	"""
	# Build player_id → fteam_abbrev from current rosters
	drafted: dict[int, str] = {
		fp.player_id: fteam.abbrev
		for fteam in fteams
		for fp in fteam.fantasyplayers
	}

	results = session.scalars(
		select(db.Result).where(db.Result.week_id == week_id)
	).all()

	player_results: dict[int, list] = defaultdict(list)
	for r in results:
		player_results[r.player_id].append(r)

	scores = []
	for player_id, maps in player_results.items():
		base_total = round(sum(sorted(
			(PointCalculator.score(r) for r in maps), reverse=True
		)[:2]), 1)
		if base_total == 0.0:
			continue
		player = session.get(db.Player, player_id)
		if not player:
			continue
		scores.append({
			"player":   player.name,
			"pro_team": player.team.abbrev if player.team else "—",
			"fteam":    drafted.get(player_id),
			"base":     base_total,
		})

	scores.sort(key=lambda x: x["base"], reverse=True)
	return scores[:n]


def week_top_map_performances(week_id: int, session: Session, n: int = 5) -> list[dict]:
	"""Return top-n single-map performances by base score for the week.

	Only considers each player's top-2 maps (consistent with scoring rules).
	Each entry includes player, pro_team, acs, kills, deaths, assists,
	mk_pts (multikill+clutch, integer), base, and map_str ('Haven vs. FUT').
	"""
	results = session.scalars(
		select(db.Result).where(db.Result.week_id == week_id)
	).all()

	player_results: dict[int, list] = defaultdict(list)
	for r in results:
		player_results[r.player_id].append(r)

	entries = []
	for player_id, maps in player_results.items():
		top2 = sorted(maps, key=lambda r: PointCalculator.score(r), reverse=True)[:2]
		for r in top2:
			player = session.get(db.Player, player_id)
			if not player:
				continue
			mk_pts = (
				r.player_2k * 2 + r.player_3k * 4 + r.player_4k * 7 + r.player_5k * 10
				+ r.player_clutch_v2 * 8 + r.player_clutch_v3 * 12
				+ r.player_clutch_v4 * 16 + r.player_clutch_v5 * 20
			)
			entries.append({
				"player":   player.name,
				"pro_team": player.team.abbrev if player.team else "?",
				"team_id":  player.team_id,
				"match_id": r.match_id,
				"map":      r.map,
				"acs":      r.player_acs,
				"kills":    r.player_kills,
				"deaths":   r.player_deaths,
				"assists":  r.player_assists,
				"mk_pts":   mk_pts,
				"base":     PointCalculator.score(r),
			})

	# Resolve opponent per match per pro team
	match_ids_by_team: dict[int, set] = defaultdict(set)
	for e in entries:
		if e["team_id"]:
			match_ids_by_team[e["team_id"]].add(e["match_id"])

	opp_lookup: dict[tuple, str] = {}
	for team_id, mids in match_ids_by_team.items():
		opp_map = build_opponent_map(mids, team_id, session)
		for mid, abbrev in opp_map.items():
			opp_lookup[(team_id, mid)] = abbrev

	for e in entries:
		opp = opp_lookup.get((e["team_id"], e["match_id"]), "?")
		e["map_str"] = f"{e['map']} vs. {opp}"

	entries.sort(key=lambda x: x["base"], reverse=True)
	return entries[:n]


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
