from fantasyVCT.scraper import Scraper

# unit testing
# Run with pytest

full = Scraper.parse_match(25206)

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

def test_player_stats():
	assert full.maps[0].team1.players[0].stats['acs'] == 275
	assert full.maps[0].team1.players[0].stats['kills'] == 29
	assert full.maps[0].team1.players[0].stats['deaths'] == 19
	assert full.maps[0].team1.players[0].stats['assists'] == 4
	assert full.maps[0].team1.players[0].stats['2k'] == 8
	assert full.maps[0].team1.players[0].stats['3k'] == 1
	assert full.maps[0].team1.players[0].stats['4k'] == 1
	assert full.maps[0].team1.players[0].stats['1v2'] == 1

def test_player_name():
	assert full.maps[1].team1.players[0].name == "Asuna"
	assert full.maps[1].team1.players[1].name == "Ethan"
	assert full.maps[1].team1.players[2].name == "nitr0"
	assert full.maps[1].team1.players[3].name == "Hiko"
	assert full.maps[1].team1.players[4].name == "steel"
	assert full.maps[1].team2.players[0].name == "dapr"
	assert full.maps[1].team2.players[1].name == "TenZ"
	assert full.maps[1].team2.players[2].name == "ShahZaM"
	assert full.maps[1].team2.players[3].name == "SicK"
	assert full.maps[1].team2.players[4].name == "zombs"

def test_player_agent():
	assert full.maps[1].team1.players[0].agent == "reyna"
	assert full.maps[1].team1.players[1].agent == "sage"
	assert full.maps[1].team1.players[2].agent == "omen"
	assert full.maps[1].team1.players[3].agent == "viper"
	assert full.maps[1].team1.players[4].agent == "skye"
	assert full.maps[1].team2.players[0].agent == "killjoy"
	assert full.maps[1].team2.players[1].agent == "jett"
	assert full.maps[1].team2.players[2].agent == "sova"
	assert full.maps[1].team2.players[3].agent == "skye"
	assert full.maps[1].team2.players[4].agent == "viper"

def test_player_agent():
	assert Scraper.parse_team("https://www.vlr.gg/team/188/cloud9-blue")

def test_scrape_resolves():
	Scraper.parse_match(109588)
	assert True


# team = Scraper.parse_team("https://www.vlr.gg/team/188/cloud9-blue")
# print(team)
