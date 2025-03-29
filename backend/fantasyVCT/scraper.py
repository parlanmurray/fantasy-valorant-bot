
import fantasyVCT.database as db

from bs4 import BeautifulSoup
import requests

vlr_performance = "https://vlr.gg/{}/?game=all&tab=performance"
vlr_summary = "https://vlr.gg/{}/?game=all"


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

	@staticmethod
	def scrape_url(url: str):
		"""Retrieve match information from a vlr.gg url as html.
		
		Args:
		    url (str): vlr.gg url as a string

		Returns:
			BeautifulSoup: Match information scraped from url
		"""
		req =  requests.get(url)
		soup = BeautifulSoup(req.text, "html.parser")

		return soup

	@staticmethod
	def _parse_player_summary(html, player):
		"""Parse an html object for player information, assuming summary tab.
		
		Args:
		    html (BeautifulSoup): html object containing player information
			player (db.Player): object to place player information in
		"""
		# parse player info
		name = html.find('td', class_="mod-player").a.div.get_text(strip=True)

		if name != player.name:
			raise ValueError(f"Player name {name} does not match destination name {player.name}")

		if not player.results:
			player.results.append(db.Result())

		player.results[0].agent = html.find('td', class_="mod-agents").img['alt']

		player_stats = html.find_all('td', class_="mod-stat")

		player.results[0].player_acs = int(player_stats[1].find('span', class_="mod-both").get_text(strip=True))
		player.results[0].player_kills = int(player_stats[2].find('span', class_="mod-both").get_text(strip=True))
		player.results[0].player_deaths = int(player_stats[3].find('span', class_="mod-both").get_text(strip=True).strip('/'))
		player.results[0].player_assists = int(player_stats[4].find('span', class_="mod-both").get_text(strip=True))

	@staticmethod
	def _parse_player_performance(html, player: db.Player):
		"""Parse an html object for player information, assuming performance tab.
		
		Args:
		    html (BeautifulSoup): html object containing player information
			player (db.Player): object to place player information in
		"""
		# parse player info
		items = html.find_all('td')
		name = " ".join(items[0].get_text().split()[:-1])
		if name != player.name:
			raise ValueError(f"Player name {name} does not match destination name {player.name}")

		# place stats inside a Result
		if not player.results:
			player.results.append(db.Result())

		stat_list = {2 : "player_2k", 3 : "player_3k", 4 : "player_4k", 5 : "player_5k", 7 : "player_clutch_v2", 8 : "player_clutch_v3", 9 : "player_clutch_v4", 10 : "player_clutch_v5"}
		for k, v in stat_list.items():
			contents = items[k].get_text().split()
			if contents:
				setattr(player.results[0], v, int(contents[0]))
			else:
				setattr(player.results[0], v, 0)

	@staticmethod
	def _parse_team_summary(html_score, html_players, team: db.Team):
		"""Parse an html object for team information.
		
		Args:
		    html_score (BeautifulSoup): html object containing score information
		    html_players (BeautifulSoup): html object containing player information
			team (db.Team): db.Team object to place team information in
		"""
		# parse score info
		team.name = html_score.find('div', class_="team-name").get_text(strip=True)
		team.won = 'mod-win' in html_score.find('div', class_="score")['class']
		team.score = int(html_score.find('div', class_="score").get_text(strip=True))

		# loop through players
		for row in html_players.tbody.find_all('tr'):
			name = row.find('td', class_="mod-player").a.div.get_text(strip=True)
			player = team.get_player(name)
			if not player:
				player = db.Player(name=name)
				team.players.append(player)
			Scraper._parse_player_summary(row, player)
			if not team.abbrev:
				team.abbrev = row.find('td', class_="mod-player").select('a > div')[1].get_text(strip=True)

	@staticmethod
	def __parse_team_performance(html, team: db.Map):
		raise NotImplementedError

	@staticmethod
	def _parse_map_summary(html, map_: db.Map):
		"""Parse an html object for summary information about a map, assuming
		summary tab.
		
		Args:
		    html (BeautifulSoup): a div containing information about a single map
			map_ (db.Map): db.Map object to place map information in
		"""
		header = html.div

		# build Map
		map_header = header.find('div', {'class': 'map'})
		map_.name = map_header.get_text().split()[0]
		game_id = int(html['data-game-id'])
		if game_id != map_.game_id:
			raise ValueError(f"game_id {game_id} does not match destination game_id {map_.game_id}")

		# build teams
		if not map_.team1:
			map_.team1 = db.Team()
		if not map_.team2:
			map_.team2 = db.Team()

		scores = header.find_all('div', {'class': 'team'})
		score1 = scores[0]
		score2 = scores[1]

		players = html.find_all('table')
		players1 = players[0]
		players2 = players[1]

		Scraper._parse_team_summary(score1, players1, map_.team1)
		Scraper._parse_team_summary(score2, players2, map_.team2)

		# set map pick
		if not map_header.find('span', class_="picked"):
			pass
		elif 'mod-1' in map_header.find('span', class_="picked")['class']:
			map_.team1.map_pick = True
		elif 'mod-2' in map_header.find('span', class_="picked")['class']:
			map_.team2.map_pick = True

	@staticmethod
	def _parse_map_performance(html, map_: db.Map):
		"""Parse an html object for performance information about a map.
		
		Args:
		    html (BeautifulSoup): a div containing informaiton about a single map
			map_ (db.Map): the Map object to place data in
		"""
		# build Map
		game_id = int(html['data-game-id'])
		if game_id != map_.game_id:
			raise ValueError(f"parsed game_id {game_id} does not match destination game_id {map_.game_id}")

		# build teams
		table = getNthDiv(html, 1).table

		if not map_.team1:
			map_.team1 = db.Team()
		if not map_.team2:
			map_.team2 = db.Team()

		# parse players
		i = 0
		for row in table.find_all('tr'):
			if i == 0:
				pass
			elif i < 6:
				items = row.find_all('td')
				name = " ".join(items[0].get_text().split()[:-1])
				player = map_.team1.get_player(name)
				if not player:
					player = db.Player(name=name)
					map_.team1.append(player)
				Scraper._parse_player_performance(row, player)
			else:
				items = row.find_all('td')
				name = " ".join(items[0].get_text().split()[:-1])
				player = map_.team2.get_player(name)
				if not player:
					player = db.Player(name=name)
					map_.team2.append(player)
				Scraper._parse_player_performance(row, player)
			i += 1

		return map_

	@staticmethod
	def _parse_match_summary(match: db.Match):
		"""Parse a vlr.gg match page's summary tab.
		
		Args:
		    match (db.Match): db.Match object to place data in
		"""
		soup = Scraper.scrape_url(vlr_summary.format(match.match_id))
		maps = soup.find_all("div", {"class": "vm-stats-game"})

		for map_div in maps:
			if map_div['data-game-id'] == 'all':
				continue
			elif "not available" in map_div.get_text():
				continue
			game_id = int(map_div['data-game-id'])
			map_ = match.get_map(game_id)
			if not map_:
				map_ = db.Map(game_id=game_id)
				match.maps.append(map_)
			Scraper._parse_map_summary(map_div, map_)

	@staticmethod
	def _parse_match_performance(match: db.Match):
		"""Parse a vlr.gg match page's performance tab.
		
		Args:
			match (db.Match): db.Match object to place data in
		"""
		soup = Scraper.scrape_url(vlr_performance.format(match.match_id))
		maps = soup.find_all('div', {'class': 'vm-stats-game'})

		for map_div in maps:
			if map_div['data-game-id'] == 'all':
				continue
			elif "not available" in map_div.get_text():
				continue
			game_id = int(map_div['data-game-id'])
			map_ = match.get_map(game_id)
			if not map_:
				map_ = db.Map(game_id=game_id)
				match.maps.append(map_)
			Scraper._parse_map_performance(map_div, map_)
			for player in map_.team1.players:
				player.results[0].match_id = match.match_id
				player.results[0].game_id = game_id
				player.results[0].map = map_.name
			for player in map_.team2.players:
				player.results[0].match_id = match.match_id
				player.results[0].game_id = game_id
				player.results[0].map = map_.name

		
	@staticmethod
	def parse_match(match_id: str) -> db.Match:
		"""Parse a vlr.gg match.
		
		Args:
		    match_id (str): id of the vlr.gg match to parse
		
		Returns:
		    db.Match: all match data parsed
		
		Raises:
		    ValueError: match_id is not parseable as an int
		"""
		# sanitize input
		try:
			match_id_int = int(match_id)
		except:
			raise ValueError("Match ID must be parseable as an int")

		match = db.Match(match_id=match_id)
		Scraper._parse_match_summary(match)
		Scraper._parse_match_performance(match)
		return match

	@staticmethod
	def parse_team(url: str):
		"""Parse a vlr.gg team page.
		"""
		html = Scraper.scrape_url(url)
		header = html.body.find('div', {'class': 'team-header'})
		body = html.body.find('div', {'class': 'team-summary-container-1'})

		team_header = getNthDiv(header, 1).div
		team_name = team_header.h1.get_text(strip=True)
		if team_header.h2:
			team_abbrev = team_header.h2.get_text(strip=True)
		else:
			team_abbrev = team_name
		roster_body = body.find('div', {'class': 'wf-card'})
		roster_players = getNthDiv(roster_body, 1)
		players = roster_players.find_all('div', {'class': 'team-roster-item'})

		player_names = list()
		for player in players:
			player_names.append(player.find('div', {'class': 'team-roster-item-name-alias'}).get_text(strip=True))

		return team_name, team_abbrev, player_names
