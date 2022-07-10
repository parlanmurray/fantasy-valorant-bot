from fantasyVCT.database import DatabaseManager
from fantasyVCT.scraper import Scraper
from fantasyVCT.scoring import Cache
from fantasyVCT.status import Status

from discord.ext import commands


class FantasyValBot(commands.Bot):
	def __init__(self, command_prefix, db_user, db_password, db_name):
		super().__init__(command_prefix)
		self.db_manager = DatabaseManager(db_user, db_password, db_name)
		self.db_manager.open()
		self.scraper = Scraper()
		self.cache = Cache()
		self.status = Status()

	async def on_ready(self):
		"""perform startup procedure
		"""
		print(f'{self.user} has connected to Discord!')
		# skip the draft if argument was supplied
		if self.skip_draft:
			self.status.skip_draft()
