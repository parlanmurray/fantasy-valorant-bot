import pytest
from fantasyVCT.scoring import PointCalculator, Cache
from fantasyVCT.database import Result


def make_result(**kwargs):
    """Build a Result with all stat fields defaulting to 0."""
    defaults = dict(
        player_acs=0, player_kills=0, player_deaths=0, player_assists=0,
        player_2k=0, player_3k=0, player_4k=0, player_5k=0,
        player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0,
    )
    defaults.update(kwargs)
    return Result(**defaults)


# --- PointCalculator ---

class TestPointCalculator:

    def test_zero_stats_score_zero(self):
        assert PointCalculator.score(make_result()) == 0.0

    def test_acs_weight(self):
        # 200 * 0.05 = 10.0
        assert PointCalculator.score(make_result(player_acs=200)) == 10.0

    def test_kills_weight(self):
        # 10 * 2 = 20.0
        assert PointCalculator.score(make_result(player_kills=10)) == 20.0

    def test_deaths_are_negative(self):
        # 5 * -1 = -5.0
        assert PointCalculator.score(make_result(player_deaths=5)) == -5.0

    def test_assists_weight(self):
        # 4 * 0.5 = 2.0
        assert PointCalculator.score(make_result(player_assists=4)) == 2.0

    def test_multikill_weights(self):
        # 2k*1 + 3k*1.5 + 4k*2 + 5k*2.5 = 1 + 1.5 + 2 + 2.5 = 7.0
        r = make_result(player_2k=1, player_3k=1, player_4k=1, player_5k=1)
        assert PointCalculator.score(r) == 7.0

    def test_clutch_weights(self):
        # v2*3 + v3*4 + v4*5 + v5*6 = 3 + 4 + 5 + 6 = 18.0
        r = make_result(player_clutch_v2=1, player_clutch_v3=1, player_clutch_v4=1, player_clutch_v5=1)
        assert PointCalculator.score(r) == 18.0

    def test_full_formula(self):
        # 200*0.05 + 10*2 + 5*(-1) + 2*0.5 + 1*1 + 0 + 0 + 0 + 1*3 = 10+20-5+1+1+3 = 30.0
        r = make_result(
            player_acs=200, player_kills=10, player_deaths=5, player_assists=2,
            player_2k=1, player_clutch_v2=1,
        )
        assert PointCalculator.score(r) == 30.0

    def test_captain_multiplier_is_1_2x(self):
        # Captain bonus is applied externally; validate expected math
        r = make_result(player_acs=200, player_kills=10, player_deaths=5, player_assists=2)
        base = PointCalculator.score(r)  # 10+20-5+1 = 26.0
        assert base == 26.0
        assert round(base * 1.2, 1) == 31.2

    def test_score_rounds_to_one_decimal(self):
        # 1 assist = 0.5, ensures rounding is applied
        r = make_result(player_assists=1)
        result = PointCalculator.score(r)
        assert result == round(result, 1)


# --- Cache ---

class TestCache:

    def test_store_and_retrieve(self):
        cache = Cache()
        cache.store(player_id=1, key=100, value=25.0)
        assert cache.retrieve(1, 100) == 25.0

    def test_retrieve_unknown_player_returns_none(self):
        cache = Cache()
        assert cache.retrieve(99) is None

    def test_retrieve_unknown_key_returns_none(self):
        cache = Cache()
        cache.store(1, 100, 25.0)
        assert cache.retrieve(1, 999) is None

    def test_retrieve_all_values_for_player(self):
        cache = Cache()
        cache.store(1, 101, 10.0)
        cache.store(1, 102, 15.0)
        all_vals = cache.retrieve(1)
        assert all_vals[101] == 10.0
        assert all_vals[102] == 15.0

    def test_retrieve_total(self):
        cache = Cache()
        cache.store(1, 101, 10.0)
        cache.store(1, 102, 15.0)
        assert cache.retrieve_total(1) == 25.0

    def test_retrieve_total_unknown_player_returns_zero(self):
        cache = Cache()
        assert cache.retrieve_total(99) == 0

    def test_invalidate_forces_recalculation(self):
        cache = Cache()
        cache.store(1, 101, 10.0)
        cache.retrieve_total(1)  # populates cached total
        cache.invalidate()
        # total is cleared; retrieve_total must recalculate correctly
        assert cache.retrieve_total(1) == 10.0

    def test_invalidate_does_not_drop_scores(self):
        cache = Cache()
        cache.store(1, 101, 10.0)
        cache.store(1, 102, 5.0)
        cache.invalidate()
        assert cache.retrieve_total(1) == 15.0

    def test_multiple_players_isolated(self):
        cache = Cache()
        cache.store(1, 101, 10.0)
        cache.store(2, 101, 99.0)
        assert cache.retrieve_total(1) == 10.0
        assert cache.retrieve_total(2) == 99.0
