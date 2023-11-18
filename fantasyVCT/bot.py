from fantasyVCT.database import DatabaseManager
from fantasyVCT.scraper import Scraper
from fantasyVCT.scoring import Cache
from fantasyVCT.status import Status

from discord.ext import commands


class FantasyValBot(commands.Bot):
	def __init__(self, command_prefix, db_user, db_password, db_name, db_type = "mysql"):
		super().__init__(command_prefix)
		self.db_manager = DatabaseManager(db_type, db_user, db_password, db_name)
		self.scraper = Scraper()
		self.cache = Cache()
		self.status = Status()
		# there are several more fields here added by argparse
		# skip_draft
		# num_rounds
		# sub_slots

	async def on_ready(self):
		"""perform startup procedure
		"""
		print(f'{self.user} has connected to Discord!')
		# skip the draft if argument was supplied
		if self.skip_draft:
			self.status.skip_draft()
		self.status.set_num_rounds(self.num_rounds)
