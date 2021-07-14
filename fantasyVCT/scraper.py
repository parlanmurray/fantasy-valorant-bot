"""Summary
"""
import pandas as pd
from valorant import Team, Player, Map

vlr_url = ""

# INSTRUCTIONS
# This is how I imagine this working, feel free to add or edit as needed.
# see valorant.py for additional TODO and useful classes
# Note that most code I wrote here is PSEUDOCODE and doesn't actually work

class Scraper:

	"""Scrapes and parses a vlr.gg match page.
	"""

	def scrape_url(self, match_code: str):

		"""Retrieve match information from a vlr.gg url as html.
		
		Args:
		    url (str): vlr.gg url as a string

		Returns:
			TYPE: Match information scraped from url
		"""
		url = 'https://www.vrl.gg/' + match_code + '/?game=all&tab=' + "overview"  # URL for overview
		html = pd.concat([pd.read_html(url)[2], pd.read_html(url)[3]])
		url1 = 'https://www.vrl.gg/' + match_code + '/?game=all&tab=' + "performance"  # URL for performance
		html1 = pd.read_html(url1)
		games1 = int(len(html1) / 4 - 1)  # Total number of games
		tables1 = list(range(games1))  # Placeholders for tables
		# Check if there are any games for given match code
		if games1 == 0:
			# TO DO: table filled with zeros
			print("No Matches Up")
		# Make tables list hold table index for each map
		for i in range(games1):
			tables1[i] = 4 * (i + 1) + 3
		for j in range(games1):
			html1 = pd.concat() # TODO: Concatonating the tables from performance
		html.rename(columns={'Unnamed: 0': 'Player'}, inplace=True)  	# Name Player column
		html.set_index("Player").join(html1.set_index("Player"))		# Join overview/performance tables based on "player" key
		html[['Player', 'Team']] = html['Player'].str.split(n=1, expand=True)  # Split Player column into Player/Team
		return html

	def parse_team(self, html) -> Team:
		"""Parse an html object for team information.
		
		Args:
		    html (TYPE): an object that contains html from a vlr.gg match page
		
		Returns:
		    Team: a Team containing information parsed from html
		"""

		rv = Team("name")

		# pseudocode for parsing html object
		html = html[cols]
		for player_subsection in html:
			rv.add_player(self.parse_player(player_subsection))
		return rv

	def parse_player(self, html) -> Player:
		"""Parse an html object for player information.
		
		Args:
		    html (TYPE): an object that contains html from a vlr.gg match page
		    Pass in the row of a singular player and return as a player
		
		Returns:
		    Player: a Player containing information parsed from html
		"""
		# example
		rv = Player("zywoo")
		rv.kills = 100

		cols = ["Player", "K", "D", "A", "ACS", "2K", "3K", "4K", "5K", "1v1", "1v2", "1v3", "1v4", "1v5"]
		html.fillna("0 0", inplace=True)  # Replace all NaN values with strings
		for i in range(len(self.cols)):
			html[[self.cols[i], 'd' + str(i)]] = html[self.cols[i]].str.split(n=1, expand=True)
		return rv

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

		return rv
