
from fantasyVCT.valorant import Team, Player, Map

import pandas
from bs4 import BeautifulSoup
import requests

vlr_performance = "https://vlr.gg/{}/?game=all&tab=performance"
vlr_summary = "https://vlr.gg/{}/?game=all"

# TODO create a scrape test to autonomously verify that the UI hasn't changed
# TODO scrape performance tab


def getNthDiv(soup, n):
	"""Return the nth child div tag of soup.
	
	Args:
	    soup (BeautifulSoup): html object to parse
	    n (int): index (starting at 0) of the div tag to return
	
	Returns:
	    BeautifulSoup: the nth child div tag of soup
	"""
	return soup.find_all('div', recursive=False)[n]


class Scraper:

	"""Scrapes and parses a vlr.gg match page.
	"""

	def scrape_url(self, url: str):
		"""Retrieve match information from a vlr.gg url as html.
		
		Args:
		    url (str): vlr.gg url as a string

		Returns:
			BeautifulSoup: Match information scraped from url
		"""
		req =  requests.get(url)
		soup = BeautifulSoup(req.text, "html.parser")

		return soup

	def parse_player(self, html) -> Player:
		"""Parse an html object for player information.
		
		Args:
		    html (BeautifulSoup): an object that contains html from a vlr.gg match page
		
		Returns:
		    Player: a Player containing information parsed from html
		"""
		# parse player info
		name = html.find('td', class_="mod-player").a.div.getText().strip()
		agent = html.find('td', class_="mod-agents").img['alt']
		player = Player(name, agent)

		player_stats = html.find_all('td', class_="mod-stat")

		player.set_stat_int("acs", player_stats[0].getText().strip())
		player.set_stat_int("kills", player_stats[1].getText().strip())
		player.set_stat_int("deaths", player_stats[2].getText().strip().strip('/'))
		player.set_stat_int("assists", player_stats[3].getText().strip())

		return player

	def parse_team(self, html_score, html_players) -> Team:
		"""Parse an html object for team information.
		
		Args:
		    html_score (BeautifulSoup): html object containing score information
		    html_players (BeautifulSoup): html object containing player information
		
		Returns:
		    Team: a Team containing information parsed from html
		"""
		# parse score info
		team_name = html_score.find('div', class_="team-name").getText().strip()
		won = 'mod-win' in html_score.find('div', class_="score")['class']
		score = int(html_score.find('div', class_="score").getText().strip())
		team = Team(team_name, won, score)

		# loop through players
		for row in html_players.table.tbody.find_all('tr'):
			team.add_player(self.parse_player(row))
		
		return team

	def parse_map(self, html):
		"""Parse an html object for information about a map.
		
		Args:
		    html (BeautifulSoup): a div containing information about a single map

		Returns:
			Map: a Map containing information parsed from html
		"""
		header = html.div.find_all('div', recursive=False)

		# build Map
		map_name = header[1].getText().split()[0]
		game_id = int(html['data-game-id'])
		map_ = Map(map_name, game_id)

		# build teams
		score1 = header[0]
		score2 = header[2]

		players = getNthDiv(html, 2)
		players1 = getNthDiv(players, 0)
		players2 = getNthDiv(players, 1)

		team1 = self.parse_team(score1, players1)
		team2 = self.parse_team(score2, players2)

		# TODO set map pick

		# add teams to map
		map_.set_team(team1)
		map_.set_team(team2)

		return map_

	def parse_match(self, game_id: str) -> list:
		"""Parse a vlr.gg match.
		
		Args:
		    game_id (str): id of the vlr.gg match to parse
		
		Returns:
		    list: list of Maps
		
		Raises:
		    ValueError: game_id is not parseable as an int
		"""
		rv = list()

		# sanitize input
		try:
			game_id_int = int(game_id)
		except:
			raise ValueError("Game ID must be parseable as an int")

		soup = self.scrape_url(vlr_summary.format(game_id))
		maps = soup.find_all("div", {"class": "vm-stats-game"})
		for map_div in maps:
			if map_div['data-game-id'] == 'all':
				continue
			rv.append(self.parse_map(map_div))

		return rv
