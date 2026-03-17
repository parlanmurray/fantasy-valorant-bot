"""Smoke test: verify all cog modules import cleanly after the interactions.py split."""
from fantasyVCT.utils import POSITIONS, add_spaces
from fantasyVCT.config_cog import ConfigCog
from fantasyVCT.fantasy_cog import FantasyCog
from fantasyVCT.stats_cog import StatsCog
from fantasyVCT.matchup_cog import MatchupCog


def test_utils_positions():
    assert POSITIONS[0] == "IGL"
    assert POSITIONS[5] == "Flex"
    assert POSITIONS[6] == "Sub1"


def test_utils_add_spaces():
    result = add_spaces("hi", 10)
    assert len("hi" + result) == 10


def test_config_cog_importable():
    assert ConfigCog is not None


def test_fantasy_cog_importable():
    assert FantasyCog is not None


def test_stats_cog_importable():
    assert StatsCog is not None


def test_matchup_cog_importable():
    assert MatchupCog is not None
