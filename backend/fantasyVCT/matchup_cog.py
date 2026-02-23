from discord.ext import commands


class MatchupCog(commands.Cog, name="Matchup"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Matchup cog: {error}")

	@commands.command()
	async def newseason(self, ctx, event_url: str):
		"""Create a new season from a vlr.gg event URL"""
		# Phase 2: scrape event page, create Season + Week records
		await ctx.send("newseason: not yet implemented")

	@commands.command()
	async def generateschedule(self, ctx):
		"""Generate a round-robin matchup schedule for the active season"""
		# Phase 2: round-robin schedule generator
		await ctx.send("generateschedule: not yet implemented")

	@commands.command()
	async def closeweek(self, ctx, week_number: int):
		"""Finalize scores for a given week"""
		# Phase 2: persist home_score/away_score to matchups rows
		await ctx.send("closeweek: not yet implemented")

	@commands.command()
	async def matchup(self, ctx, week: int = None):
		"""Show your matchup for the current (or specified) week"""
		# Phase 4
		await ctx.send("matchup: not yet implemented")

	@commands.command()
	async def schedule(self, ctx):
		"""Show the full season matchup schedule"""
		# Phase 4
		await ctx.send("schedule: not yet implemented")

	@commands.command()
	async def record(self, ctx):
		"""Show W/L/T standings for the active season"""
		# Phase 4
		await ctx.send("record: not yet implemented")


async def setup(bot):
	await bot.add_cog(MatchupCog(bot))
