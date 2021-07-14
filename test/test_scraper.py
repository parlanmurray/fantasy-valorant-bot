from fantasyVCT.scraper import Scraper

# unit testing

scraper = Scraper()
maps = scraper.parse_match(25206)

def test_map_names():
	assert len(maps) == 2
	assert maps[0].name == "Haven"
	assert maps[1].name == "Breeze"

def test_team_name():
	assert maps[0].team1.name == "100 Thieves"
	assert maps[0].team2.name == "Sentinels"

def test_player_acs():
	assert maps[1].team1.players[0].stats['acs'] == 241

test_map_names()

# Run with pytest
