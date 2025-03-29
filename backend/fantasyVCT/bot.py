from fantasyVCT.database import DatabaseManager
from fantasyVCT.scraper import Scraper
from fantasyVCT.scoring import Cache
from fantasyVCT.draft_state import DraftState

from discord.ext import commands
from discord import Intents


class FantasyValBot(commands.Bot):
	def __init__(self, command_prefix):
		super().__init__(command_prefix, intents=Intents.all())
		self.db_manager = None
		self.scraper = Scraper()
		self.cache = Cache()
		self.draft_state = DraftState()
		# there are several more fields here added by argparse
		# skip_draft
		# num_rounds
		# sub_slots
		# prod

	def configure_db(self, db_user, db_password, db_dev, db_prod, db_host, db_port, db_type="mysql"):
		if self.prod:
			self.db_manager = DatabaseManager(db_type, db_user, db_password, db_prod, host=db_host, port=db_port)
		else:
			self.db_manager = DatabaseManager(db_type, db_user, db_password, db_dev, host=db_host, port=db_port)
		

	async def on_ready(self):
		"""perform startup procedure
		"""
		print(f'{self.user} has connected to Discord!')
		# skip the draft if argument was supplied
		if self.skip_draft:
			self.draft_state.skip_draft()
		self.draft_state.set_num_rounds(self.num_rounds)
