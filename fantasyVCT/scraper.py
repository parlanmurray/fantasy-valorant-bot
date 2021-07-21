
from fantasyVCT.valorant import Tab, Player, Team, Map, Match

import pandas
from bs4 import BeautifulSoup
import requests

vlr_performance = "https://vlr.gg/{}/?game=all&tab=performance"
vlr_summary = "https://vlr.gg/{}/?game=all"

# TODO verify 200 response from request
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

	def parse_player_summary(self, html) -> Player:
		"""Parse an html object for player information.
		
		Args:
		    html (BeautifulSoup): an object that contains html from a vlr.gg match page
		
		Returns:
		    Player: a Player containing information parsed from html
		"""
		# parse player info
		name = html.find('td', class_="mod-player").a.div.get_text(strip=True)
		agent = html.find('td', class_="mod-agents").img['alt']
		player = Player(name, agent)

		player_stats = html.find_all('td', class_="mod-stat")

		player.set_stat_int("acs", player_stats[0].get_text(strip=True))
		player.set_stat_int("kills", player_stats[1].get_text(strip=True))
		player.set_stat_int("deaths", player_stats[2].get_text(strip=True).strip('/'))
		player.set_stat_int("assists", player_stats[3].get_text(strip=True))

		return player

	def parse_player_performance(self, html) -> Player:
		# parse player info
		items = html.find_all('td')
		name = items[0].get_text().split()[0]
		player = Player(name)

		stat_list = {2 : "2k", 3 : "3k", 4 : "4k", 5 : "5k", 7 : "1v2", 8 : "1v3", 9 : "1v4", 10 : "1v5"}
		for k, v in stat_list.items():
			contents = items[k].get_text().split()
			if contents:
				player.set_stat_int(v, contents[0])

		return player

	def parse_team_summary(self, html_score, html_players) -> Team:
		"""Parse an html object for team information.
		
		Args:
		    html_score (BeautifulSoup): html object containing score information
		    html_players (BeautifulSoup): html object containing player information
		
		Returns:
		    Team: a Team containing information parsed from html
		"""
		# parse score info
		team_name = html_score.find('div', class_="team-name").get_text(strip=True)
		won = 'mod-win' in html_score.find('div', class_="score")['class']
		score = int(html_score.find('div', class_="score").get_text(strip=True))
		team = Team(team_name, won, score)

		# loop through players
		for row in html_players.table.tbody.find_all('tr'):
			team.add_player(self.parse_player_summary(row))
		
		return team

	def parse_team_performance(self, html) -> Player:
		raise NotImplementedError

	def parse_map_summary(self, html) -> Map:
		"""Parse an html object for summary information about a map.
		
		Args:
		    html (BeautifulSoup): a div containing information about a single map

		Returns:
			Map: a Map containing information parsed from html
		"""
		header = html.div.find_all('div', recursive=False)

		# build Map
		map_name = header[1].get_text().split()[0]
		game_id = int(html['data-game-id'])
		map_ = Map(game_id, name=map_name)

		# build teams
		score1 = header[0]
		score2 = header[2]

		players = getNthDiv(html, 2)
		players1 = getNthDiv(players, 0)
		players2 = getNthDiv(players, 1)

		team1 = self.parse_team_summary(score1, players1)
		team2 = self.parse_team_summary(score2, players2)

		# TODO set map pick

		# add teams to map
		map_.set_team(team1)
		map_.set_team(team2)

		return map_

	def parse_map_performance(self, html) -> Map:
		"""Parse an html object for performance information about a map.
		"""
		# build Map
		game_id = int(html['data-game-id'])
		map_ = Map(game_id)

		# build teams
		table = getNthDiv(html, 1).table

		team1 = Team("performance1")
		team2 = Team("performance2")

		# parse players
		i = 0
		for row in table.find_all('tr'):
			if i == 0:
				pass
			elif i < 6:
				team1.add_player(self.parse_player_performance(row))
			else:
				team2.add_player(self.parse_player_performance(row))
			i += 1

		map_.set_team(team1)
		map_.set_team(team2)

		return map_

	def parse_match_summary(self, game_id: int) -> Match:
		"""Parse a vlr.gg match page's summary tab.
		
		Args:
		    game_id (int): id of the vlr.gg match to parse
		
		Returns:
		    Match: summary tab match data parsed
		"""
		soup = self.scrape_url(vlr_summary.format(game_id))
		maps = soup.find_all("div", {"class": "vm-stats-game"})
		match_summary = Match(game_id, Tab.SUMMARY)

		for map_div in maps:
			if map_div['data-game-id'] == 'all':
				continue
			elif "not available" in map_div.get_text():
				continue
			match_summary.add_map(self.parse_map_summary(map_div))

		return match_summary

	def parse_match_performance(self, game_id: int) -> Match:
		"""Parse a vlr.gg match page's performance tab.
		
		Args:
		    game_id (int): id of the vlr.gg match to parse
		
		Returns:
		    Match: performance tab match data parsed
		"""
		soup = self.scrape_url(vlr_performance.format(game_id))
		maps = soup.find_all('div', {'class': 'vm-stats-game'})
		match_performance = Match(game_id, Tab.PERFORMANCE)

		for map_div in maps:
			if map_div['data-game-id'] == 'all':
				continue
			elif "not available" in map_div.get_text():
				continue
			match_performance.add_map(self.parse_map_performance(map_div))

		return match_performance
		
	def parse_match(self, game_id: str) -> Match:
		"""Parse a vlr.gg match.
		
		Args:
		    game_id (str): id of the vlr.gg match to parse
		
		Returns:
		    Match: all match data parsed
		
		Raises:
		    ValueError: game_id is not parseable as an int
		"""
		# sanitize input
		try:
			game_id_int = int(game_id)
		except:
			raise ValueError("Game ID must be parseable as an int")

		match_summary = self.parse_match_summary(game_id_int)
		match_performance = self.parse_match_performance(game_id_int)
		return match_summary.combine(match_performance)
