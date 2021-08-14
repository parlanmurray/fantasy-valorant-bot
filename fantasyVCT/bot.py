from fantasyVCT.database import DatabaseManager

from discord.ext import commands


class FantasyValBot(commands.Bot):
	def __init__(self, command_prefix, database_user, database_password):
		super().__init__(command_prefix)
		self.db_manager = DatabaseManager(database_user, database_password)

	async def on_ready(self):
		"""Summary
		"""
		print(f'{self.user} has connected to Discord!')
