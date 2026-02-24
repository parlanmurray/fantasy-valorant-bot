"""P3 — Scraper unit/edge-case tests.
No live network required; uses crafted HTML and mocks.
"""
import pytest
from unittest.mock import patch
from bs4 import BeautifulSoup

from fantasyVCT.scraper import Scraper
import fantasyVCT.database as db


# ── Helpers ───────────────────────────────────────────────────────────────────

def _perf_row(name, abbrev="SEN", stats=None):
    """Build a minimal performance-tab <tr> for _parse_player_performance.

    items[0]  = "name abbrev"
    items[2]  = player_2k
    items[3]  = player_3k
    items[4]  = player_4k
    items[5]  = player_5k
    items[7]  = player_clutch_v2
    items[8]  = player_clutch_v3
    items[9]  = player_clutch_v4
    items[10] = player_clutch_v5
    All unspecified cells are empty strings (parsed as 0).
    """
    cells = [""] * 11
    cells[0] = f"{name} {abbrev}"
    if stats:
        for idx, val in stats.items():
            cells[idx] = str(val)
    tds = "".join(f"<td>{c}</td>" for c in cells)
    return BeautifulSoup(f"<table><tr>{tds}</tr></table>", "html.parser").find("tr")


def _game_divs_html(*game_ids, body="valid content"):
    """Build a soup with vm-stats-game divs for the given game_ids."""
    divs = "".join(
        f'<div class="vm-stats-game" data-game-id="{gid}">{body}</div>'
        for gid in game_ids
    )
    return BeautifulSoup(f"<html><body>{divs}</body></html>", "html.parser")


# ── Invalid match ID ──────────────────────────────────────────────────────────

class TestInvalidMatchId:
    def test_non_numeric_raises(self):
        with pytest.raises(ValueError):
            Scraper.parse_match("not-a-number")

    def test_float_string_raises(self):
        with pytest.raises(ValueError):
            Scraper.parse_match("12.5")

    def test_alphanumeric_raises(self):
        with pytest.raises(ValueError):
            Scraper.parse_match("123abc")


# ── _parse_player_performance ─────────────────────────────────────────────────

class TestParsePlayerPerformance:
    def test_empty_cells_yield_zero_stats(self):
        player = db.Player(name="TenZ")
        row = _perf_row("TenZ")
        Scraper._parse_player_performance(row, player)
        r = player.results[0]
        assert r.player_2k == 0
        assert r.player_3k == 0
        assert r.player_4k == 0
        assert r.player_5k == 0
        assert r.player_clutch_v2 == 0
        assert r.player_clutch_v3 == 0
        assert r.player_clutch_v4 == 0
        assert r.player_clutch_v5 == 0

    def test_nonzero_stats_parsed(self):
        player = db.Player(name="aspas")
        row = _perf_row("aspas", stats={2: 3, 3: 2, 4: 1, 5: 1, 7: 2, 8: 1, 9: 0, 10: 0})
        Scraper._parse_player_performance(row, player)
        r = player.results[0]
        assert r.player_2k == 3
        assert r.player_3k == 2
        assert r.player_4k == 1
        assert r.player_5k == 1
        assert r.player_clutch_v2 == 2
        assert r.player_clutch_v3 == 1
        assert r.player_clutch_v4 == 0
        assert r.player_clutch_v5 == 0

    def test_name_mismatch_raises(self):
        player = db.Player(name="TenZ")
        row = _perf_row("aspas")
        with pytest.raises(ValueError):
            Scraper._parse_player_performance(row, player)

    def test_reuses_existing_result(self):
        """If player already has a result, stats are written into results[0]."""
        player = db.Player(name="Boaster")
        existing = db.Result()
        player.results.append(existing)
        row = _perf_row("Boaster", stats={2: 5})
        Scraper._parse_player_performance(row, player)
        assert len(player.results) == 1
        assert player.results[0].player_2k == 5


# ── Summary/performance map filtering ────────────────────────────────────────

class TestMatchSummaryFiltering:
    def test_skips_all_game_id(self):
        """`data-game-id="all"` divs are excluded."""
        soup = _game_divs_html("all")
        with patch.object(Scraper, "scrape_url", return_value=soup), \
             patch.object(Scraper, "_parse_map_summary") as mock_parse:
            match = db.Match(match_id=1)
            Scraper._parse_match_summary(match)
            mock_parse.assert_not_called()
            assert len(match.maps) == 0

    def test_skips_not_available_maps(self):
        """`not available` text in a map div is excluded."""
        soup = _game_divs_html(42, body="not available")
        with patch.object(Scraper, "scrape_url", return_value=soup), \
             patch.object(Scraper, "_parse_map_summary") as mock_parse:
            match = db.Match(match_id=1)
            Scraper._parse_match_summary(match)
            mock_parse.assert_not_called()
            assert len(match.maps) == 0


class TestMatchPerformanceFiltering:
    def test_skips_all_and_not_available(self):
        soup = _game_divs_html("all", 99, body="not available")
        with patch.object(Scraper, "scrape_url", return_value=soup), \
             patch.object(Scraper, "_parse_map_performance") as mock_parse:
            match = db.Match(match_id=1)
            Scraper._parse_match_performance(match)
            mock_parse.assert_not_called()
            assert len(match.maps) == 0
