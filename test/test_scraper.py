from fantasyVCT.scraper import Scraper

# unit testing

scraper = Scraper()
maps = scraper.parse_match(25206)

def test_map_names():
	assert len(maps) == 3
	assert maps[0].name == "Haven"
	assert maps[1].name == "Breeze"
	assert maps[2].name == "Ascent"

def test_map_played():
	assert maps[0].was_played == True
	assert maps[2].was_played == False

def test_map_number():
	assert maps[0].number is 1

def test_team_name():
	assert maps[0].team1.name == "100 Thieves"
	assert maps[0].team2.name == "Sentinels"

def test_player_acs():
	assert maps[1].team1.players[0].stats['acs'] == 241

test_map_names()

# Run with pytest
