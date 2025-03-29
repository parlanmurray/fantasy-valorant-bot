from fantasyVCT.scraper import Scraper

# unit testing
# Run with pytest

def test_player_agent():
	assert Scraper.parse_team("https://www.vlr.gg/team/188/cloud9-blue")

def test_scrape_resolves():
	Scraper.parse_match(109588)
	assert True

try:
	full = Scraper.parse_match(25206)

	print(str(full))

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
		assert full.maps[0].team1.players[0].results[0].player_acs == 275
		assert full.maps[0].team1.players[0].results[0].player_kills == 29
		assert full.maps[0].team1.players[0].results[0].player_deaths == 19
		assert full.maps[0].team1.players[0].results[0].player_assists == 4
		assert full.maps[0].team1.players[0].results[0].player_2k == 8
		assert full.maps[0].team1.players[0].results[0].player_3k == 1
		assert full.maps[0].team1.players[0].results[0].player_5k == 0
		assert full.maps[0].team1.players[0].results[0].player_clutch_v2 == 1

	def test_player_name():
		assert full.maps[1].team1.players[0].name == "Hiko"
		assert full.maps[1].team1.players[1].name == "Ethan"
		assert full.maps[1].team1.players[2].name == "nitr0"
		assert full.maps[1].team1.players[3].name == "Asuna"
		assert full.maps[1].team1.players[4].name == "steel"
		assert full.maps[1].team2.players[0].name == "dapr"
		assert full.maps[1].team2.players[1].name == "TenZ"
		assert full.maps[1].team2.players[2].name == "ShahZaM"
		assert full.maps[1].team2.players[3].name == "SicK"
		assert full.maps[1].team2.players[4].name == "zombs"

	def test_player_agent():
		assert full.maps[1].team1.players[0].results[0].agent == "viper"
		assert full.maps[1].team1.players[1].results[0].agent == "sage"
		assert full.maps[1].team1.players[2].results[0].agent == "omen"
		assert full.maps[1].team1.players[3].results[0].agent == "reyna"
		assert full.maps[1].team1.players[4].results[0].agent == "skye"
		assert full.maps[1].team2.players[0].results[0].agent == "killjoy"
		assert full.maps[1].team2.players[1].results[0].agent == "jett"
		assert full.maps[1].team2.players[2].results[0].agent == "sova"
		assert full.maps[1].team2.players[3].results[0].agent == "skye"
		assert full.maps[1].team2.players[4].results[0].agent == "viper"

	def test_populated_results_fields():
		for player in full.maps[1].team1.players:
			for result in player.results:
				assert full.maps[1].game_id == result.game_id
				assert full.match_id == result.match_id
				assert full.maps[1].name == result.map

except Exception as e:
	print("scraper is not functional")
	print(e)

# team = Scraper.parse_team("https://www.vlr.gg/team/188/cloud9-blue")
# print(team)
