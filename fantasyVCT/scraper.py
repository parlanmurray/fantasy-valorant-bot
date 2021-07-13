"""Summary
"""
import pandas as pd
from fantasyVCT.valorant import Team, Player, Map

vlr_url = "https://vlr.gg/"

# INSTRUCTIONS
# This is how I imagine this working, feel free to add or edit as needed.
# see valorant.py for additional TODO and useful classes
# Note that most code I wrote here is PSEUDOCODE and doesn't actually work

class Scraper:

	"""Scrapes and parses a vlr.gg match page.
	"""

	def scrape_url(self, url: str):
		"""Retrieve match information from a vlr.gg url as html.
		
		Args:
		    url (str): vlr.gg url as a string

		Returns:
			TYPE: Match information scraped from url
		"""
		results =  pd.read_html(url)
		print(results)
		return results


	def parse_team(self, html) -> Team:
		"""Parse an html object for team information.
		
		Args:
		    html (TYPE): an object that contains html from a vlr.gg match page
		
		Returns:
		    Team: a Team containing information parsed from html
		"""
		rv = Team("name")

		# pseudocode for parsing html object
		for player_subsection in html:
			rv.add_player(self.parse_player(player_subsection))
		
		return rv

	def parse_player(self, html) -> Player:
		"""Parse an html object for player information.
		
		Args:
		    html (TYPE): an object that contains html from a vlr.gg match page
		
		Returns:
		    Player: a Player containing information parsed from html
		"""
		# example
		rv = Player("zywoo")
		rv.kills = 100

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

		results = self.scrape_url(vlr_url + str(game_id) + "/")

		return rv
