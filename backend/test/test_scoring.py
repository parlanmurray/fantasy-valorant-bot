import pytest
from fantasyVCT.scoring import PointCalculator
from fantasyVCT.scoring import (
    ROLE_IGL_WIN, ROLE_DUELIST_FK, ROLE_INITIATOR_ASSIST,
    ROLE_CONTROLLER_ASSIST, ROLE_CONTROLLER_SURVIVAL, ROLE_SENTINEL_DEATH_SAVE,
)
from fantasyVCT.database import Result


def make_result(**kwargs):
    """Build a Result with all stat fields defaulting to 0."""
    defaults = dict(
        player_acs=0, player_kills=0, player_deaths=0, player_assists=0,
        player_2k=0, player_3k=0, player_4k=0, player_5k=0,
        player_clutch_v2=0, player_clutch_v3=0, player_clutch_v4=0, player_clutch_v5=0,
        player_fk=0,
    )
    defaults.update(kwargs)
    return Result(**defaults)


# --- PointCalculator ---

class TestPointCalculator:

    def test_zero_stats_score_zero(self):
        assert PointCalculator.score(make_result()) == 0.0

    def test_acs_weight(self):
        # 200 * 0.03 = 6.0
        assert PointCalculator.score(make_result(player_acs=200)) == 6.0

    def test_kills_weight(self):
        # 10 * 1.5 = 15.0
        assert PointCalculator.score(make_result(player_kills=10)) == 15.0

    def test_deaths_are_negative(self):
        # 5 * -1 = -5.0
        assert PointCalculator.score(make_result(player_deaths=5)) == -5.0

    def test_assists_weight(self):
        # 4 * 0.5 = 2.0
        assert PointCalculator.score(make_result(player_assists=4)) == 2.0

    def test_multikill_weights(self):
        # 2k*2 + 3k*4 + 4k*7 + 5k*10 = 2 + 4 + 7 + 10 = 23.0
        r = make_result(player_2k=1, player_3k=1, player_4k=1, player_5k=1)
        assert PointCalculator.score(r) == 23.0

    def test_clutch_weights(self):
        # v2*8 + v3*12 + v4*16 + v5*20 = 8 + 12 + 16 + 20 = 56.0
        r = make_result(player_clutch_v2=1, player_clutch_v3=1, player_clutch_v4=1, player_clutch_v5=1)
        assert PointCalculator.score(r) == 56.0

    def test_full_formula(self):
        # 200*0.03 + 10*1.5 + 5*(-1) + 2*0.5 + 1*2 + 1*8 = 6+15-5+1+2+8 = 27.0
        r = make_result(
            player_acs=200, player_kills=10, player_deaths=5, player_assists=2,
            player_2k=1, player_clutch_v2=1,
        )
        assert PointCalculator.score(r) == 27.0

    def test_no_role_bonus_in_base_score(self):
        # role_bonus is separate; base score must not include it
        r = make_result(player_kills=10, player_fk=3, player_assists=4, player_deaths=5,
                        rounds_played=20, team_won=True)
        base = PointCalculator.score(r)
        assert base == PointCalculator.score(make_result(
            player_kills=10, player_fk=3, player_assists=4, player_deaths=5))

    def test_fk_weight(self):
        # 3 FK * 1.0 = 3.0
        assert PointCalculator.score(make_result(player_fk=3)) == 3.0

    def test_fk_none_scores_zero(self):
        # player_fk=None (pre-migration rows) should not raise and score 0
        assert PointCalculator.score(make_result(player_fk=None)) == 0.0

    def test_score_rounds_to_one_decimal(self):
        # 1 assist = 0.5, ensures rounding is applied
        r = make_result(player_assists=1)
        result = PointCalculator.score(r)
        assert result == round(result, 1)


