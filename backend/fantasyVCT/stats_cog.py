import fantasyVCT.database as db

from discord.ext import commands
from sqlalchemy import select

from fantasyVCT.scoring import PointCalculator
from fantasyVCT.utils import build_opponent_map


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
				num_maps = len(player.results)
				total    = round(sum(PointCalculator.score(row) for row in player.results), 1)
				ppm      = round(total / num_maps, 1) if num_maps > 0 else 0.0

				# Build opponent lookup (always shown)
				match_ids    = list({row.match_id for row in player.results})
				opponent_map = build_opponent_map(set(match_ids), player.team_id, session)

				# Build week lookup (h2h only)
				week_map = {}
				if self.bot.h2h:
					week_ids = list({row.week_id for row in player.results if row.week_id})
					if week_ids:
						week_rows = session.execute(
							select(db.Week.id, db.Week.week_number).where(db.Week.id.in_(week_ids))
						).all()
						week_map = {wid: wnum for wid, wnum in week_rows}

				buf = f"```\n{player.name} - {ppm} PPM\n"
				buf += f"    Team: {player.team.name}\n"
				buf += "\n"
				buf += "    Match Results\n"

				if self.bot.h2h:
					line = f"      Wk"
					line = f"{line:<10}Opponent"
					line = f"{line:<22}Points"
					line = f"{line:<30}ACS"
					line = f"{line:<38}K/D/A"
					line = f"{line:<48}Game ID\n"
					buf += line
					for row in player.results:
						week_num = week_map.get(row.week_id)
						week_label = f"W{week_num}" if week_num else "--"
						opp_abbrev = opponent_map.get(row.match_id)
						opponent = f"vs. {opp_abbrev}" if opp_abbrev else "vs. ?"
						pts = PointCalculator.score(row)
						line = f"      {week_label}"
						line = f"{line:<10}{opponent}"
						line = f"{line:<22}{pts}"
						line = f"{line:<30}{row.player_acs}"
						line = f"{line:<38}{row.player_kills}/{row.player_deaths}/{row.player_assists}"
						line = f"{line:<48}{row.game_id}\n"
						buf += line
				else:
					line = f"      Points"
					line = f"{line:<14}ACS"
					line = f"{line:<22}K/D/A"
					line = f"{line:<32}Opponent"
					line = f"{line:<42}Game ID\n"
					buf += line
					for row in player.results:
						opp_abbrev = opponent_map.get(row.match_id)
						opponent = f"vs. {opp_abbrev}" if opp_abbrev else "vs. ?"
						pts = PointCalculator.score(row)
						line = f"      {pts}"
						line = f"{line:<14}{row.player_acs}"
						line = f"{line:<22}{row.player_kills}/{row.player_deaths}/{row.player_assists}"
						line = f"{line:<32}{opponent}"
						line = f"{line:<42}{row.game_id}\n"
						buf += line

				buf += "```"
				return await ctx.send(buf)

		await ctx.send("A team or player was not found for {}.".format(query_string))

	@commands.command()
	async def rankplayers(self, ctx):
		"""Rank all pro players by fantasy points, highest to lowest."""

		def get_fantasy_points(player):
			return round(sum(PointCalculator.score(row) for row in player.results), 1)

		buf = "```Player Rankings\n"
		line = f"    Player"
		line = f"{line:<30}Points"
		line = f"{line:<40}Fantasy Team\n\n"
		buf += line

		with self.bot.db_manager.create_session() as session:
			players = list(session.scalars(select(db.Player)))
			players = sorted(players, key=lambda player: get_fantasy_points(player), reverse=True)
			for player in players:
				line = f"    {player.team.abbrev} {player.name}"
				line = f"{line:<30}{get_fantasy_points(player)}"
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
