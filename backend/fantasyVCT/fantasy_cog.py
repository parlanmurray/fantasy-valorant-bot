import typing

import fantasyVCT.database as db

from discord.ext import commands
import discord
from sqlalchemy import select, or_

from fantasyVCT.scoring import PointCalculator
from fantasyVCT.matchup import compute_weekly_score, derive_record, get_season_chain
from fantasyVCT.utils import add_spaces, POSITIONS


class FantasyCog(commands.Cog, name="Fantasy"):
	def __init__(self, bot):
		self.bot = bot
		self.pos_max = min(10, 6 + bot.sub_slots)

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Fantasy cog: {error}")

	@commands.command()
	async def draft(self, ctx, player_name: str):
		"""Pick a player during the draft or add a free agent to your roster.

		Parameters:
		-----------
		player_name: Player's exact IGN (case-sensitive). Use !freeagents to see available players.
		"""
		author_id = ctx.message.author.id

		if not self.bot.draft_state.is_draft_started():
			return await ctx.send("Draft has not started yet!")
		elif not self.bot.draft_state.can_draft(author_id):
			return await ctx.send("It is not your turn yet!")

		with self.bot.db_manager.create_session() as session:
			drafted_player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
			if not drafted_player:
				return await ctx.send(f"No player was found for \"{player_name}\"")

			if drafted_player.fantasyplayer:
				return await ctx.send(f"{drafted_player.name} has already been drafted to a fantasy team.")

			user = session.execute(select(db.User).filter_by(discord_id=author_id)).scalar_one_or_none()
			if not user:
				return await ctx.send("You are not registered. Please use the `!register` command to register. Type `!help` for more informaiton.")
			elif not user.fantasyteam:
				return await ctx.send("You do not have a fantasy team. Please use the `!register` command to create a fantasy team. Type `!help` for more information.")

			drafted_fp = None
			sub_flag = False
			placed_flag = False
			for i in range(self.pos_max):
				if sub_flag and i < 6:
					continue
				skip_flag = False
				for fp in user.fantasyteam.fantasyplayers:
					if fp.position == i:
						if i > 0 and i < 6 and drafted_player.team and fp.player.team == drafted_player.team:
							sub_flag = True
						skip_flag = True
						break

				if skip_flag or drafted_fp:
					continue

				drafted_fp = db.FantasyPlayer(position=i)
				drafted_fp.player = drafted_player
				drafted_fp.fantasyteam = user.fantasyteam
				session.add(drafted_fp)

				session.flush()
				session.commit()
				placed_flag = True
				break

		if placed_flag:
			await ctx.invoke(self.bot.get_command('roster'))

			if self.bot.draft_state.is_draft_started() and not self.bot.draft_state.is_draft_complete():
				next_drafter = self.bot.draft_state.next()
				if next_drafter:
					await ctx.send(f"It is <@!{next_drafter}>'s turn to draft!")
				else:
					await ctx.send("Initial draft is complete!")
			return

		return await ctx.send("You do not have a spot for this player on your roster. Use `!drop` if you want to make space. Type `!help` for more information.")

	@commands.command()
	async def drop(self, ctx, player_name: str):
		"""Release a player from your roster back to free agency.

		Parameters:
		-----------
		player_name: Player's exact IGN (case-sensitive). Use !roster to see your current players.
		"""
		author_id = ctx.message.author.id

		if not self.bot.draft_state.is_draft_complete():
			return await ctx.send("Cannot drop players until initial draft is complete.")

		with self.bot.db_manager.create_session() as session:
			dropped_player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
			if not dropped_player:
				return await ctx.send(f"No player was found for \"{player_name}\"")

			user = session.execute(select(db.User).filter_by(discord_id=author_id)).scalar_one_or_none()
			if not dropped_player.fantasyplayer or dropped_player.fantasyplayer not in user.fantasyteam.fantasyplayers:
				return await ctx.send(f"No player {dropped_player.name} found on your roster. Try the `!roster` command. Type `!help` for more information.")

			session.delete(dropped_player.fantasyplayer)
			session.flush()
			session.commit()

			await ctx.send(f"{dropped_player.name} is now a free agent!")

	@commands.command()
	async def roster(self, ctx, member: typing.Optional[discord.Member] = None, team: typing.Optional[str] = None):
		"""Display a fantasy team's roster and points. Defaults to your own team.

		Parameters:
		-----------
		member: @mention a Discord user to view their roster (optional).
		team: Team abbreviation or name to view (optional).
		"""

		with self.bot.db_manager.create_session() as session:
			fantasy_team = None

			if member:
				user = session.execute(select(db.User).filter_by(discord_id=member.id)).scalar_one_or_none()
				if not user or not user.fantasyteam:
					return await ctx.send(f"{member.name} does not have a registered fantasy team.")
				fantasy_team = user.fantasyteam
			elif team:
				fantasy_team = session.execute(select(db.FantasyTeam).where(
					or_(
						db.FantasyTeam.name == team,
						db.FantasyTeam.abbrev == team
					)
				)).scalar_one_or_none()
				if not fantasy_team:
					return await ctx.send(f"No fantasy team found for {team}")
			else:
				author = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
				if not author or not author.fantasyteam:
					return await ctx.send("You do not have a registered fantasy team. Use the `!register` command. Type `!help` for more information.")
				fantasy_team = author.fantasyteam

			fantasy_players = fantasy_team.fantasyplayers

			buf = "```\n" + fantasy_team.abbrev + " / " + fantasy_team.name
			total = 0
			buf2 = ""
			for k in range(self.pos_max):
				line = add_spaces("", 4) + str(POSITIONS[k])
				for fp in fantasy_players:
					if fp.position is k:
						line += add_spaces(line, 16) + f"{fp.player.team.abbrev} {fp.player.name}"
						for row in fp.player.results:
							fantasy_points = self.bot.cache.retrieve(fp.player.id, row.game_id)
							if not fantasy_points:
								fantasy_points = PointCalculator.score(row)
								self.bot.cache.store(fp.player.id, row.game_id, fantasy_points)
						player_points = self.bot.cache.retrieve_total(fp.player.id)
						if k == 0:
							player_points = player_points * 1.2
						if k < 6:
							total += player_points
						line += add_spaces(line, 36) + str(round(player_points, 1))
						if k == 0:
							line += " (1.2x)"
						break
				buf2 += line + "\n"
				if k == 5:
					buf2 += "\n"
			buf += " -- " + str(round(total, 1)) + "\n"
			line = ""
			line += add_spaces(line, 4) + "Position"
			line += add_spaces(line, 16) + "Name"
			line += add_spaces(line, 36) + "Points"
			buf += line + "\n\n"
			buf += buf2 + "```"
			await ctx.send(buf)

	@commands.command()
	async def freeagents(self, ctx):
		"""List all undrafted players and their fantasy points."""

		with self.bot.db_manager.create_session() as session:
			stmt = select(db.Player).where(db.Player.id.notin_(select(db.FantasyPlayer.player_id)))
			free_agents = session.scalars(stmt)

			buf = "```\nFree Agents\n"
			line = add_spaces("", 4) + "Player"
			line += add_spaces(line, 24) + "Points"
			buf += line + "\n\n"
			for player in free_agents:
				for row in player.results:
					fantasy_points = self.bot.cache.retrieve(player.id, row.game_id)
					if not fantasy_points:
						fantasy_points = PointCalculator.score(row)
						self.bot.cache.store(player.id, row.game_id, fantasy_points)
				player_points = self.bot.cache.retrieve_total(player.id)
				line = add_spaces("", 4) + f"{player.team.abbrev} {player.name}"
				line += add_spaces(line, 24) + str(player_points)

				if len(buf + line) > 1900:
					buf += "```"
					await ctx.send(buf)
					buf = "```\nFree Agents (page 2)\n"
					line2 = add_spaces("", 4) + "Player"
					line2 += add_spaces(line, 24) + "Points"
					buf += line2 + "\n\n"
				buf += line + "\n"
			buf += "```"
			await ctx.send(buf)

	@commands.command()
	async def set(self, ctx, player: str, position: str):
		"""Move a player to a different position on your roster.

		Parameters:
		-----------
		player: Player's exact IGN (case-sensitive).
		position: Target position (captain, player1–player5, sub1–sub4).
		"""

		if not position.lower() in (string.lower() for string in POSITIONS.values()):
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")
		dest_pos = list(POSITIONS.keys())[list(string.lower() for string in POSITIONS.values()).index(position.lower())]
		if dest_pos >= self.pos_max:
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")

		with self.bot.db_manager.create_session() as session:
			set_player = session.execute(select(db.Player).filter_by(name=player)).scalar_one_or_none()
			if not set_player:
				return await ctx.send(f"No player was not found for \"{player}\".")

			user = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
			if set_player.fantasyplayer not in user.fantasyteam.fantasyplayers:
				return await ctx.send(f"{set_player.name} is not on your roster.")

			dest_player = session.execute(select(db.FantasyPlayer).filter_by(fantasy_team_id=user.fantasy_team_id, position=dest_pos)).scalar_one_or_none()
			if dest_player:
				dest_player.position = set_player.fantasyplayer.position
				set_player.fantasyplayer.position = dest_pos
			else:
				set_player.fantasyplayer.position = dest_pos

			existing_teams = list()
			for curr_player in user.fantasyteam.fantasyplayers:
				if curr_player.position > 0 and curr_player.position < 6:
					if curr_player.player.team in existing_teams:
						session.rollback()
						return await ctx.send("Cannot assign player to this position due to team restriction. See !rules.")
					else:
						existing_teams.append(curr_player.player.team)

			session.flush()
			session.commit()
			await ctx.invoke(self.bot.get_command('roster'))

	@commands.command()
	async def standings(self, ctx):
		"""Show current fantasy league standings sorted by optimized score."""

		with self.bot.db_manager.create_session() as session:
			fteams = list(session.scalars(select(db.FantasyTeam)))

			# Compute season points
			for fteam in fteams:
				total = 0
				for fp in fteam.fantasyplayers:
					if fp.position < 6:
						for row in fp.player.results:
							fantasy_points = self.bot.cache.retrieve(fp.player.id, row.game_id)
							if not fantasy_points:
								fantasy_points = PointCalculator.score(row)
								self.bot.cache.store(fp.player.id, row.game_id, fantasy_points)
						player_points = self.bot.cache.retrieve_total(fp.player.id)
						if fp.position == 0:
							player_points = player_points * 1.2
						total = round(total + player_points, 1)
				fteam.points = total

			# Compute W/L/T if there's an active season (walk all stages)
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			team_records = {}
			if season:
				chain = get_season_chain(season)
				all_season_ids = [s.id for s in chain]
				chain_week_ids = select(db.Week.id).where(db.Week.season_id.in_(all_season_ids))
				for fteam in fteams:
					matchups = list(session.scalars(
						select(db.Matchup).where(
							(db.Matchup.home_team_id == fteam.id) | (db.Matchup.away_team_id == fteam.id),
							db.Matchup.week_id.in_(chain_week_ids)
						)
					))
					closed = [m for m in matchups if m.home_score > 0 or m.away_score > 0]
					team_records[fteam.id] = derive_record(closed, fteam.id)

			# Sort by wins (if H2H active), then total points
			if team_records:
				sorted_teams = sorted(fteams, key=lambda k: (-team_records[k.id][0], -k.points))
			else:
				sorted_teams = sorted(fteams, key=lambda k: k.points, reverse=True)

			buf = "```\nStandings\n\n"
			if team_records:
				buf += f"  {'Team':<18} {'W':<4}{'L':<4}{'T':<4}{'Pts'}\n\n"
				for fteam in sorted_teams:
					w, l, t = team_records[fteam.id]
					name = f"{fteam.abbrev} / {fteam.name}"
					buf += f"  {name:<18} {w:<4}{l:<4}{t:<4}{fteam.points}\n"
			else:
				for fteam in sorted_teams:
					buf += f"\t{fteam.abbrev} / {fteam.name} - {str(fteam.points)}\n"
			buf += "```"
			await ctx.send(buf)


async def setup(bot):
	await bot.add_cog(FantasyCog(bot))
