from fantasyVCT.database import DatabaseManager
from fantasyVCT.scraper import Scraper
from fantasyVCT.scoring import Cache
from fantasyVCT.status import Status
from fantasyVCT.vlr_api import get_results

from discord.ext import commands


class FantasyValBot(commands.Bot):
	def __init__(self, command_prefix, db_user, db_password, db_name):
		super().__init__(command_prefix)
		self.db_manager = DatabaseManager(db_user, db_password, db_name)
		self.db_manager.open()
		self.scraper = Scraper()
		self.cache = Cache()
		self.status = Status()

	def process_results(self, json):
		if json['data']['status'] != 200:
			return

		# create a list of match results with tournament name and the match page id
		for game in json['data']['segments']:
			if self.db_manager.query_events_from_name(game['tournament_name']):
				match_id = game['match_page'].split('/')[1]
				if not self.db_manager.query_results_all_from_game_id(match_id):
					ctx = self.get_context()
					cmd = self.get_command('upload')
					await ctx.invoke(cmd, vlr_id=match_id)

	async def on_ready(self):
		"""Summary
		"""
		print(f'{self.user} has connected to Discord!')
