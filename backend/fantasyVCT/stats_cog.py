import fantasyVCT.database as db

from discord.ext import commands
from sqlalchemy import select

from fantasyVCT.scoring import PointCalculator


class StatsCog(commands.Cog, name="Stats"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Stats cog: {error}")

	@commands.command()
	async def info(self, ctx, *args: str):
		"""Look up a pro player or team's stats and fantasy points.

		Parameters:
		-----------
		query: Player IGN or team name/abbreviation.
		"""
		query_string = " ".join(args)

		with self.bot.db_manager.create_session() as session:
			team = session.execute(select(db.Team).filter_by(name=query_string)).scalar_one_or_none()
			if team:
				buf = "```\n" + str(team.name)
				for player in team.players:
					buf += "\n    " + str(player.name)
				buf += "```"
				return await ctx.send(buf)

			player = session.execute(select(db.Player).filter_by(name=query_string)).scalar_one_or_none()
			if player:
				for row in player.results:
					fantasy_points = self.bot.cache.retrieve(player.id, row.game_id)
					if not fantasy_points:
						fantasy_points = PointCalculator.score(row)
						self.bot.cache.store(player.id, row.game_id, fantasy_points)
				total = self.bot.cache.retrieve_total(player.id)

				buf = f"```\n{player.name} - {str(total)}\n"
				buf += f"    Team: {player.team.name}\n"
				buf += "\n"
				buf += "    Match Results\n"
				line = f"        Points"
				line = f"{line:<16}ACS"
				line = f"{line:<24}K/D/A"
				line = f"{line:<34}Game ID\n"
				buf += line
				for row in player.results:
					line = f"        {self.bot.cache.retrieve(player.id, row.game_id)}"
					line = f"{line:<16}{row.player_acs}"
					line = f"{line:<24}{row.player_kills}/{row.player_deaths}/{row.player_assists}"
					line = f"{line:<34}{row.game_id}\n"
					buf += line
				buf += "```"
				return await ctx.send(buf)

		await ctx.send("A team or player was not found for {}.".format(query_string))

	@commands.command()
	async def rankplayers(self, ctx):
		"""Rank all pro players by fantasy points, highest to lowest."""

		def get_fantasy_points(cache, player):
			total = cache.retrieve_total(player.id)
			if not total:
				for row in player.results:
					fantasy_points = self.bot.cache.retrieve(player.id, row.game_id)
					if not fantasy_points:
						fantasy_points = PointCalculator.score(row)
						cache.store(player.id, row.game_id, fantasy_points)
				total = cache.retrieve_total(player.id)
			return total

		buf = "```Player Rankings\n"
		line = f"    Player"
		line = f"{line:<30}Points"
		line = f"{line:<40}Fantasy Team\n\n"
		buf += line

		with self.bot.db_manager.create_session() as session:
			players = list(session.scalars(select(db.Player)))
			players = sorted(players, key=lambda player: get_fantasy_points(self.bot.cache, player), reverse=True)
			for player in players:
				line = f"    {player.team.abbrev} {player.name}"
				line = f"{line:<30}{self.bot.cache.retrieve_total(player.id)}"
				if player.fantasyplayer:
					line = f"{line:<40}{player.fantasyplayer.fantasyteam.abbrev}"

				if len(buf + line) > 1900:
					buf += "```"
					await ctx.send(buf)
					buf = "```\nPlayer Rankings (page 2)\n"
					line2 = f"    Player"
					line2 = f"{line2:<30}Points"
					line2 = f"{line2:<40}Fantasy Team\n"
					buf += line2 + "\n\n"
				buf += line + "\n"

		buf += "```"
		return await ctx.send(buf)


async def setup(bot):
	await bot.add_cog(StatsCog(bot))
