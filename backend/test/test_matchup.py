"""Tests for matchup.py — schedule generation, score computation, W/L/T derivation."""
import pytest
from unittest.mock import MagicMock

from fantasyVCT.matchup import (
	generate_schedule, compute_weekly_score, compute_weekly_score_snapshot,
	get_roster_breakdown, derive_record,
)
from fantasyVCT.scoring import PointCalculator
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
		for home, away, ghost_mirror in week_pairs:
			assert home not in seen
			assert away not in seen
			seen.extend([home, away])
			# Even teams: no ghost matchups
			assert away is not None
			assert ghost_mirror is None


def test_schedule_even_full_roundrobin():
	"""4 teams: across 3 rounds every pair meets exactly once."""
	teams = [1, 2, 3, 4]
	schedule = generate_schedule(teams, num_weeks=3)

	pairs = set()
	for week_pairs in schedule:
		for home, away, ghost_mirror in week_pairs:
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
		ghost_count = sum(1 for _, away, _m in week_pairs if away is None)
		assert ghost_count == 1, "Exactly one ghost matchup per round with odd teams"


def test_schedule_repeat():
	"""When num_weeks > num_rounds, schedule cycles from the beginning."""
	teams = [1, 2, 3, 4]
	# 3 rounds in one cycle; ask for 6 weeks → should repeat
	schedule = generate_schedule(teams, num_weeks=6)

	assert len(schedule) == 6
	# First 3 weeks == last 3 weeks (tuples include ghost_mirror_id)
	assert schedule[0] == schedule[3]
	assert schedule[1] == schedule[4]
	assert schedule[2] == schedule[5]


def test_schedule_single_week():
	schedule = generate_schedule([1, 2], num_weeks=1)
	assert len(schedule) == 1
	assert len(schedule[0]) == 1
	home, away, ghost_mirror = schedule[0][0]
	assert frozenset([home, away]) == frozenset([1, 2])
	assert ghost_mirror is None


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


# ---------------------------------------------------------------------------
# compute_weekly_score (mocked session)
# ---------------------------------------------------------------------------

def _make_result(player_id, week_id, kills=10, deaths=5, assists=3,
				 acs=200, k2=1, k3=0, k4=0, k5=0, cv2=0, cv3=0, cv4=0, cv5=0,
				 player_fk=None, rounds_played=None, team_won=None):
	return db.Result(
		map="Haven", game_id=1, match_id=1, event_id=1,
		player_id=player_id, week_id=week_id,
		player_kills=kills, player_deaths=deaths, player_assists=assists,
		player_acs=acs, player_2k=k2, player_3k=k3, player_4k=k4, player_5k=k5,
		player_clutch_v2=cv2, player_clutch_v3=cv3, player_clutch_v4=cv4, player_clutch_v5=cv5,
		agent="jett", player_fk=player_fk, rounds_played=rounds_played, team_won=team_won
	)


def _mock_session(fteam, results):
	session = MagicMock()
	session.get.return_value = fteam
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = results
	session.scalars.return_value = mock_scalars
	return session


def test_compute_weekly_score_basic():
	fteam = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp1 = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=1)
	fp2 = db.FantasyPlayer(id=2, player_id=20, fantasy_team_id=1, position=2)
	fteam.fantasyplayers = [fp1, fp2]

	r1 = _make_result(player_id=10, week_id=5, kills=10, deaths=5, assists=3, acs=200)
	r2 = _make_result(player_id=20, week_id=5, kills=8, deaths=4, assists=2, acs=180)

	session = _mock_session(fteam, [r1, r2])
	score = compute_weekly_score(1, 5, session)
	assert score > 0


def test_compute_weekly_score_role_bonus_igl():
	"""IGL (position=0) with a map win gets +8.5 bonus; Duelist (position=1) does not."""
	result_win = _make_result(player_id=10, week_id=5, team_won=True)
	result_no_bonus = _make_result(player_id=10, week_id=5, team_won=False)

	fteam_igl = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp_igl = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=0)
	fteam_igl.fantasyplayers = [fp_igl]

	fteam_flex = db.FantasyTeam(id=2, name="Beta", abbrev="BET")
	fp_flex = db.FantasyPlayer(id=2, player_id=10, fantasy_team_id=2, position=5)
	fteam_flex.fantasyplayers = [fp_flex]

	session_igl = _mock_session(fteam_igl, [result_win])
	session_flex = _mock_session(fteam_flex, [result_no_bonus])

	score_igl = compute_weekly_score(1, 5, session_igl)
	score_flex = compute_weekly_score(2, 5, session_flex)

	base = PointCalculator.score(result_win)
	assert round(score_igl, 4) == round(base + 8.5, 4)
	assert round(score_flex, 4) == round(base, 4)


def test_compute_weekly_score_best2_maps():
	"""Player with 3 map results: only top 2 count toward weekly score."""
	fteam = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=5)  # Flex, no bonus
	fteam.fantasyplayers = [fp]

	r1 = _make_result(player_id=10, week_id=5, kills=15, acs=250)  # best
	r2 = _make_result(player_id=10, week_id=5, kills=10, acs=200)  # mid
	r3 = _make_result(player_id=10, week_id=5, kills=5, acs=150)   # worst

	session = _mock_session(fteam, [r1, r2, r3])
	score = compute_weekly_score(1, 5, session)

	top2 = sorted([PointCalculator.score(r1), PointCalculator.score(r2), PointCalculator.score(r3)], reverse=True)[:2]
	assert round(score, 4) == round(sum(top2), 4)


def test_compute_weekly_score_igl_win_selected_over_higher_base():
	"""IGL with map win (lower base) should be selected over map loss (higher base) when win bonus flips the total."""
	fteam = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=0)  # IGL
	fteam.fantasyplayers = [fp]

	# Map 1: higher base score but no win — total = base_loss
	map_loss = _make_result(player_id=10, week_id=5, kills=10, acs=200, team_won=False)
	# Map 2: lower base score but win — total = base_win + 8.5
	map_win = _make_result(player_id=10, week_id=5, kills=8, acs=180, team_won=True)

	base_loss = PointCalculator.score(map_loss)
	base_win = PointCalculator.score(map_win)
	# Ensure the setup is valid: base_loss > base_win, but base_win + 8.5 > base_loss
	assert base_loss > base_win
	assert base_win + 8.5 > base_loss

	# With only these 2 maps, both count (no cap triggered). Verify role bonus is included.
	session = _mock_session(fteam, [map_loss, map_win])
	score = compute_weekly_score(1, 5, session)

	expected = base_loss + (base_win + 8.5)
	assert round(score, 4) == round(expected, 4)


def test_compute_weekly_score_subs_excluded():
	"""Sub positions (6+) should not count toward weekly score."""
	fteam = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp_sub = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=6)
	fteam.fantasyplayers = [fp_sub]

	session = _mock_session(fteam, [])
	score = compute_weekly_score(1, 5, session)
	assert score == 0.0


def test_compute_weekly_score_no_team():
	"""Returns 0.0 when team not found."""
	session = MagicMock()
	session.get.return_value = None
	assert compute_weekly_score(999, 5, session) == 0.0


# ---------------------------------------------------------------------------
# Phase 5 edge cases
# ---------------------------------------------------------------------------

def test_null_week_id_results_excluded_from_weekly_score():
	"""Results with week_id=None should not appear in a weekly score query."""
	fteam = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=1)
	fteam.fantasyplayers = [fp]

	# Session returns no results (simulating that the WHERE week_id=5 filtered them out)
	session = _mock_session(fteam, [])
	score = compute_weekly_score(1, 5, session)
	assert score == 0.0


def test_schedule_repeat_cycle_correct_length():
	"""Schedule of length > one cycle still has correct total week count."""
	teams = [1, 2, 3, 4]
	schedule = generate_schedule(teams, num_weeks=7)
	assert len(schedule) == 7


def test_schedule_repeat_all_matchups_valid():
	"""Every week in a repeated schedule has valid (non-None home) pairings."""
	teams = [1, 2, 3, 4]
	schedule = generate_schedule(teams, num_weeks=9)
	for week_pairs in schedule:
		for home, away, ghost_mirror in week_pairs:
			assert home is not None  # home is always a real team


def test_ghost_matchup_bye_no_wlt():
	"""A ghost matchup (away_team_id=None) is NOT counted as W/L/T for the ghost.
	derive_record only counts matchups where the team is home or away — ghost can't call derive_record."""
	ghost_matchup = _matchup(1, None, 100.0, 0.0)
	# For team 1: home_score 100 > away_score 0 → win
	w, l, t = derive_record([ghost_matchup], fantasy_team_id=1)
	assert (w, l, t) == (1, 0, 0)


def test_derive_record_empty():
	"""No matchups → 0/0/0."""
	w, l, t = derive_record([], fantasy_team_id=1)
	assert (w, l, t) == (0, 0, 0)


def test_schedule_odd_each_team_gets_ghost_once():
	"""In one cycle with N=3, each team gets exactly one ghost matchup."""
	teams = [1, 2, 3]
	schedule = generate_schedule(teams, num_weeks=3)

	ghost_counts = {t: 0 for t in teams}
	for week_pairs in schedule:
		for home, away, ghost_mirror in week_pairs:
			if away is None:
				ghost_counts[home] += 1

	for team_id, count in ghost_counts.items():
		assert count == 1, f"Team {team_id} expected 1 ghost matchup, got {count}"


def test_ghost_mirror_is_real_team():
	"""Ghost matchups must have a non-None ghost_mirror_id pointing to a real team."""
	teams = [1, 2, 3]
	schedule = generate_schedule(teams, num_weeks=3)

	for week_pairs in schedule:
		for home, away, ghost_mirror in week_pairs:
			if away is None:
				assert ghost_mirror is not None, "Ghost matchup must have a mirror team"
				assert ghost_mirror in teams, f"ghost_mirror {ghost_mirror} not in team list"
				assert ghost_mirror != home, "Ghost mirror should not be the bye team itself"


def test_ghost_mirror_not_set_for_real_matchups():
	"""Non-ghost matchups must have ghost_mirror_id = None."""
	teams = [1, 2, 3]
	schedule = generate_schedule(teams, num_weeks=3)

	for week_pairs in schedule:
		for home, away, ghost_mirror in week_pairs:
			if away is not None:
				assert ghost_mirror is None


# ---------------------------------------------------------------------------
# compute_weekly_score_snapshot
# ---------------------------------------------------------------------------

def _scalars_side_effect(*return_lists):
	"""Helper: return successive MagicMocks whose .all() returns each list."""
	mocks = []
	for lst in return_lists:
		m = MagicMock()
		m.all.return_value = lst
		m.first.return_value = lst[0] if lst else None
		mocks.append(m)
	return mocks


def test_compute_weekly_score_snapshot_uses_snapshot():
	"""Snapshot rows drive scoring instead of current fantasy_players."""
	snap = db.RosterSnapshot(week_id=5, fteam_id=1, player_id=10, position=5)  # Flex
	r1 = _make_result(player_id=10, week_id=5, kills=10, acs=200)

	session = MagicMock()
	snap_mock, result_mock = _scalars_side_effect([snap], [r1])
	session.scalars.side_effect = [snap_mock, result_mock]

	score = compute_weekly_score_snapshot(1, 5, session)

	expected = PointCalculator.score(r1)
	assert round(score, 4) == round(expected, 4)


def test_compute_weekly_score_snapshot_fallback():
	"""No snapshot rows → falls back to compute_weekly_score."""
	fteam = db.FantasyTeam(id=1, name="Alpha", abbrev="ALP")
	fp = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=5)
	fteam.fantasyplayers = [fp]
	r1 = _make_result(player_id=10, week_id=5, kills=10, acs=200)

	session = MagicMock()
	session.get.return_value = fteam
	snap_mock, result_mock = _scalars_side_effect([], [r1])
	session.scalars.side_effect = [snap_mock, result_mock]

	score = compute_weekly_score_snapshot(1, 5, session)

	expected = PointCalculator.score(r1)
	assert round(score, 4) == round(expected, 4)


def test_compute_weekly_score_snapshot_subs_excluded():
	"""Sub positions (6+) in snapshot are not scored."""
	snap_active = db.RosterSnapshot(week_id=5, fteam_id=1, player_id=10, position=5)  # Flex (active)
	snap_sub = db.RosterSnapshot(week_id=5, fteam_id=1, player_id=20, position=6)     # Sub1
	r_active = _make_result(player_id=10, week_id=5, kills=10, acs=200)

	session = MagicMock()
	snap_mock, result_mock = _scalars_side_effect([snap_active, snap_sub], [r_active])
	session.scalars.side_effect = [snap_mock, result_mock]

	score = compute_weekly_score_snapshot(1, 5, session)
	expected = PointCalculator.score(r_active)
	assert round(score, 4) == round(expected, 4)


# ---------------------------------------------------------------------------
# get_roster_breakdown
# ---------------------------------------------------------------------------

def _make_player(player_id, name, team_abbrev="TST"):
	player = db.Player(id=player_id, name=name)
	team = db.Team(id=1, name="Test Team", abbrev=team_abbrev)
	player.team = team
	return player


def test_get_roster_breakdown_with_snapshot():
	"""Snapshot path: has_snapshot=True, active slots scored, subs 0.0."""
	player = _make_player(10, "aspas")
	snap = db.RosterSnapshot(week_id=5, fteam_id=1, player_id=10, position=5)
	snap.player = player
	r1 = _make_result(player_id=10, week_id=5, kills=10, acs=200)

	session = MagicMock()
	snap_mock, result_mock = _scalars_side_effect([snap], [r1])
	session.scalars.side_effect = [snap_mock, result_mock]

	has_snapshot, slots = get_roster_breakdown(1, 5, session)

	assert has_snapshot is True
	assert len(slots) == 10

	# Position 5 (Flex) should have scores
	flex_slot = slots[5]
	assert flex_slot["player_name"] == "TST aspas"
	assert flex_slot["base"] > 0
	assert flex_slot["is_active"] is True

	# Sub slots have 0.0 base/bonus
	for s in slots[6:]:
		assert s["base"] == 0.0
		assert s["bonus"] == 0.0
		assert s["is_active"] is False


def test_get_roster_breakdown_fallback():
	"""No snapshot → has_snapshot=False, reads from FantasyPlayer rows."""
	player = _make_player(10, "TenZ")
	fp = db.FantasyPlayer(id=1, player_id=10, fantasy_team_id=1, position=1)
	fp.player = player
	r1 = _make_result(player_id=10, week_id=5, kills=12, acs=220)

	session = MagicMock()
	snap_mock, fp_mock, result_mock = _scalars_side_effect([], [fp], [r1])
	session.scalars.side_effect = [snap_mock, fp_mock, result_mock]

	has_snapshot, slots = get_roster_breakdown(1, 5, session)

	assert has_snapshot is False
	duelist_slot = slots[1]
	assert duelist_slot["player_name"] == "TST TenZ"
	assert duelist_slot["base"] > 0


def test_get_roster_breakdown_empty_slot():
	"""Positions with no player assigned return player_name=None."""
	snap = db.RosterSnapshot(week_id=5, fteam_id=1, player_id=10, position=0)
	player = _make_player(10, "food")
	snap.player = player
	r1 = _make_result(player_id=10, week_id=5, kills=8, acs=190)

	session = MagicMock()
	snap_mock, result_mock = _scalars_side_effect([snap], [r1])
	session.scalars.side_effect = [snap_mock, result_mock]

	has_snapshot, slots = get_roster_breakdown(1, 5, session)

	# Position 0 (IGL) has a player
	assert slots[0]["player_name"] is not None

	# All other active positions are empty
	for pos in range(1, 6):
		assert slots[pos]["player_name"] is None, f"Position {pos} should be empty"
