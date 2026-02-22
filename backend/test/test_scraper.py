from fantasyVCT.scraper import Scraper
import pytest

# Fetch once at module level; any parse failure will fail all tests explicitly.
full = Scraper.parse_match(25206)


def _by_name(players):
    """Return dict of {name: player} for easy lookup."""
    return {p.name: p for p in players}


# --- team / map structure ---

def test_map_names():
    assert len(full.maps) == 2
    assert full.maps[0].name == "Haven"
    assert full.maps[1].name == "Breeze"

def test_team_name():
    assert full.maps[0].team1.name == "100 Thieves"
    assert full.maps[0].team2.name == "Sentinels"

def test_team_abbrev():
    assert full.maps[0].team1.abbrev == "100T"
    assert full.maps[0].team2.abbrev == "SEN"

def test_team_won():
    assert full.maps[0].team2.won
    assert not full.maps[0].team1.won
    assert full.maps[1].team2.won
    assert not full.maps[1].team1.won

def test_team_score():
    assert full.maps[0].team1.score == 13
    assert full.maps[0].team2.score == 15
    assert full.maps[1].team1.score == 8
    assert full.maps[1].team2.score == 13


# --- player presence (order-independent) ---

def test_player_name():
    """All expected players are present; don't assert ordering (vlr.gg sorts by ACS)."""
    t1 = {p.name for p in full.maps[1].team1.players}
    assert {"Hiko", "Ethan", "nitr0", "Asuna", "steel"} == t1

    t2 = {p.name for p in full.maps[1].team2.players}
    assert {"dapr", "TenZ", "ShahZaM", "SicK", "zombs"} == t2


# --- player stats (anchored by name, not index) ---

def test_player_stats():
    """Validate Asuna's Haven stats; anchored by name."""
    asuna = _by_name(full.maps[0].team1.players)["Asuna"]
    r = asuna.results[0]
    assert r.player_acs == 275
    assert r.player_kills == 29
    assert r.player_deaths == 19
    assert r.player_assists == 4
    assert r.player_2k == 8
    assert r.player_3k == 1
    assert r.player_5k == 0
    assert r.player_clutch_v2 == 1

def test_player_agent():
    """Validate agents by player name, not list index."""
    t1 = _by_name(full.maps[1].team1.players)
    assert t1["Hiko"].results[0].agent == "viper"
    assert t1["Ethan"].results[0].agent == "sage"
    assert t1["nitr0"].results[0].agent == "omen"
    assert t1["Asuna"].results[0].agent == "reyna"
    assert t1["steel"].results[0].agent == "skye"

    t2 = _by_name(full.maps[1].team2.players)
    assert t2["dapr"].results[0].agent == "killjoy"
    assert t2["TenZ"].results[0].agent == "jett"
    assert t2["ShahZaM"].results[0].agent == "sova"
    assert t2["SicK"].results[0].agent == "skye"
    assert t2["zombs"].results[0].agent == "viper"


# --- result metadata ---

def test_populated_results_fields():
    for player in full.maps[1].team1.players:
        for result in player.results:
            assert full.maps[1].game_id == result.game_id
            assert full.match_id == result.match_id
            assert full.maps[1].name == result.map


# --- parse_team smoke test ---

def test_parse_team():
    team_name, team_abbrev, player_names = Scraper.parse_team("https://www.vlr.gg/team/188/cloud9-blue")
    assert team_name
    assert team_abbrev
    assert len(player_names) > 0


# --- recent match smoke test ---

def test_scrape_resolves():
    Scraper.parse_match(109588)
