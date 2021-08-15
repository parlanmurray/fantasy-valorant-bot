from enum import Enum

from discord.ext import commands


class Category(Enum):
	TEAM = 1
	PLAYER = 2

	@staticmethod
	def from_str(label):
		if label.upper() in ('TEAM', 'TEAMS'):
			return Category.TEAM
		elif label.upper() in ('PLAYER', 'PLAYERS'):
			return Category.PLAYER
		else:
			raise ValueError


class Test(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def hello(self, ctx):
		await ctx.send("Hello {0.name}".format(ctx.author))


class DatabaseCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def info(self, ctx, category: str, member: str):
		# TODO
		cat_type = Category.from_str(category)
		# could throw an error, do nothing for now
		# discord will print to stderr
		# may want to handle this later 
		# https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html#error-handling
		
		if cat_type is Category.TEAM:
			team_name = self.bot.db_manager.query_team_all_from_name(member)[1]
			rv = self.bot.db_manager.query_team_players_from_name(member)
			buf = "```{}:".format(team_name)
			for row in rv:
				buf += "\n\t" + row[0]
			buf += "```"
			await ctx.send(buf)
		elif cat_type is Category.PLAYER:
			pass
