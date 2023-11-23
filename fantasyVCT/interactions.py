from enum import Enum
import re
import typing

from fantasyVCT.scoring import PointCalculator
import fantasyVCT.database as db

from discord.ext import commands
import discord
from sqlalchemy import select, or_


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

POSITIONS = {
	0 : "Captain",
	1 : "Player1",
	2 : "Player2",
	3 : "Player3",
	4 : "Player4",
	5 : "Player5",
	6 : "Sub1",
	7 : "Sub2",
	8 : "Sub3",
	9 : "Sub4"
}

def add_spaces(buff, length):
	"""
	Add spaces until the buffer is at least the provided length.
	"""
	rv = ""
	while (len(buff) + len(rv)) < length:
		rv += " "
	return rv


class ConfigCog(commands.Cog, name="Configuration"):
	def __init__(self, bot):
		self.bot = bot

	# Cog error handler
	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Config cog: {error}")

	@commands.command()
	async def register(self, ctx, team_abbrev: str, *team_name_list: str):
		"""Register a team"""
		team_name = " ".join(team_name_list)

		# get author's unique id
		author_id = ctx.message.author.id

		with self.bot.db_manager.create_session() as session:
			# check that user is not already registered
			stmt = select(db.User).filter_by(discord_id=author_id)
			author = session.execute(stmt).scalar_one_or_none()
			if author and author.fantasyteam:
				return await ctx.send("You have already registered a team.")
				
			# check that team_abbrev or team_name are not taken\
			fteams = session.scalars(select(db.FantasyTeam).where(
				or_(
					db.FantasyTeam.name == team_name,
					db.FantasyTeam.abbrev == team_abbrev
				)
			))
			for fteam in fteams:
				if fteam.name == team_name:
					return await ctx.send(f"{team_name} is taken, please choose another name.")
				elif fteam.abbrev == team_abbrev:
					return await ctx.send(f"{team_abbrev} is taken, please choose another abbreviation.")

			# register user
			if not author:
				author = db.User(discord_id=author_id)
				
			# register team
			new_fteam = db.FantasyTeam(name=team_name, abbrev=team_abbrev)

			# register team to user
			author.fantasyteam = new_fteam

			# commit transaction
			session.add_all([author, new_fteam])
			session.flush()
			session.commit()

		# reply
		await ctx.send(f"{team_abbrev} / {team_name} has been registered for {ctx.message.author.mention}")

	@commands.command()
	async def skipdraft(self, ctx):
		"""Skip past the draft step."""
		self.bot.draft_state.skip_draft()

	@commands.command()
	async def trackevent(self, ctx, event_name: str):
		"""Start tracking matches from an event"""
		with self.bot.db_manager.create_session() as session:
			event = session.execute(select(db.Event).filter_by(name=event_name)).scalar_one_or_none()
			if event:
				return await ctx.send(f"{event_name} is already being tracked.")

			event = db.Event(name=event_name)
			session.add(event)
			session.flush()
			session.commit()

		await ctx.send(f"Started tracking {event_name}.")

	@commands.command()
	async def untrackevent(self, ctx, event_name: str):
		"""Stop tracking new matches from an event"""
		with self.bot.db_manager.create_session() as session:
			event = session.execute(select(db.Event).filter_by(name=event_name)).scalar_one_or_none()
			if not event:
				return await ctx.send("{event_name} is not currently being tracked.")
		
			session.delete(event)
			session.flush()
			session.commit()

		await ctx.send(f"Stopped tracking {event_name}.")

	@commands.command()
	async def startdraft(self, ctx):
		"""Begin the draft"""
		if self.bot.draft_state.is_draft_complete():
			return await ctx.send("Draft is already complete.")
		elif self.bot.draft_state.is_draft_started():
			return await ctx.send("Draft has already begun.")
		
		with self.bot.db_manager.create_session() as session:
			registered_users = session.scalars(select(db.User.discord_id))
			users_list = list(registered_users)

			# start draft
			next_drafter = self.bot.draft_state.start_draft(users_list)
			await ctx.send(f"It is <@!{next_drafter}>'s turn!")

	@commands.command()
	async def newteam(self, ctx, url: str):
		"""Upload a team and players to the database using a vlr.gg team url"""
		if self.bot.draft_state.is_draft_started():
			return await ctx.send("Cannot add additional teams/players once draft has started.")
		team_name, team_abbrev, player_names = self.bot.scraper.parse_team(url)

		with self.bot.db_manager.create_session() as session:
			# check if team exists in database
			team = session.execute(select(db.Team).filter_by(name=team_name)).scalar_one_or_none()
			if not team:
				# team does not exist in database
				team = db.Team(name=team_name, abbrev=team_abbrev)
				session.add(team)
			
			for player_name in player_names:
				# check that players exist in database
				player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
				if not player:
					# player does not exist in database
					player = db.Player(name=player_name)
					session.add(player)
				player.team = team
			session.flush()
			session.commit()
			return await ctx.invoke(self.bot.get_command('info'), team_name)

	@commands.command()
	async def rules(self, ctx):
		"""Display rules"""
		buf = "```\n"
		buf += "How to play:\n"
		buf += "- Draft a team of valorant players, and compete to see who whose players have the best performance over the course of the event\n"
		buf += "- Players will receive points based on their performance in the games\n"
		buf += "- During the draft phase, participants will take turns picking players for their teams\n"
		buf == "- Until the draft phase is over, you will not be able to add or drop players outside of your turn\n"
		buf += "- After the draft phase, you can add, drop and move players as much as you'd like\n"
		buf += "- Each team can only have ONE player from a given team. i.e. you can only have one member of 100 Thieves on your active roster\n"
		buf += "- Each team has 6 active slots and " + str(self.bot.sub_slots) + " sub slot(s)\n"
		buf += "- The Captain role is a special role that does not follow the 'one player from each team' restriction. You can have a player from ANY team as your flex, even if you already have a player from that team\n"
		buf += "- Only players in active slots count towards your team's total points\n"
		buf += "- At the end of the event, the fantasy team with the most total points wins\n"
		buf += "\n"
		buf += "Draft phase:\n"
		buf += "- There will be " + str(self.bot.num_rounds) + " rounds\n"
		buf += "- Snake draft (1234554321123...)\n"
		buf += "- The draft is asynchronous, and you will be pinged when it is your turn to draft\n"
		buf += "```"
		return await ctx.send(buf)


	@commands.command()
	async def scoring(self, ctx):
		"""Display scoring information"""
		buf = "```\n"
		buf += PointCalculator.get_scoring_info()
		buf += "```"
		return await ctx.send(buf)


class FantasyCog(commands.Cog, name="Fantasy"):
	def __init__(self, bot):
		self.bot = bot
		self.pos_max = min(10, 6 + bot.sub_slots)

	# Cog error handler
	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Fantasy cog: {error}")

	@commands.command()
	async def draft(self, ctx, player_name: str):
		"""Pick up a free agent"""
		author_id = ctx.message.author.id

		# check draft state
		if not self.bot.draft_state.is_draft_started():
			return await ctx.send("Draft has not started yet!")
		elif not self.bot.draft_state.can_draft(author_id):
			return await ctx.send("It is not your turn yet!")

		with self.bot.db_manager.create_session() as session:
			# search for player
			drafted_player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
			if not drafted_player:
				return await ctx.send(f"No player was found for \"{player_name}\"")

			# check that player isn't already on a team
			if drafted_player.fantasyplayer:
				return await ctx.send(f"{drafted_player.name} has already been drafted to a fantasy team.")

			# check that the user has a valorant roster
			user = session.execute(select(db.User).filter_by(discord_id=author_id)).scalar_one_or_none()
			if not user:
				return await ctx.send("You are not registered. Please use the `!register` command to register. Type `!help` for more informaiton.")
			elif not user.fantasyteam:
				return await ctx.send("You do not have a fantasy team. Please use the `!register` command to create a fantasy team. Type `!help` for more information.")
			
			# find a spot on the roster for the player
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

				# place player on roster in current position
				drafted_fp = db.FantasyPlayer(position=i)
				drafted_fp.player = drafted_player
				drafted_fp.fantasyteam = user.fantasyteam
				session.add(drafted_fp)
				
				# commit changes and print new roster info
				session.flush()
				session.commit()
				placed_flag = True
				break

		if placed_flag:
			await ctx.invoke(self.bot.get_command('roster'))

			# update draft status
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
		"""Drop a player from your team"""
		author_id = ctx.message.author.id

		# check draft state
		if not self.bot.draft_state.is_draft_complete():
			return await ctx.send("Cannot drop players until initial draft is complete.")
		
		with self.bot.db_manager.create_session() as session:
			# search for player
			dropped_player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
			if not dropped_player:
				return await ctx.send(f"No player was found for \"{player_name}\"")

			# check that player is on user's roster
			user = session.execute(select(db.User).filter_by(discord_id=author_id)).scalar_one_or_none()
			if not dropped_player.fantasyplayer or dropped_player.fantasyplayer not in user.fantasyteam.fantasyplayers:
				return await ctx.send(f"No player {dropped_player.name} found on your roster. Try the `!roster` command. Type `!help` for more information.")

			# drop player
			session.delete(dropped_player.fantasyplayer)
			session.flush()
			session.commit()

			await ctx.send(f"{dropped_player.name} is now a free agent!")

	@commands.command()
	async def roster(self, ctx, member: typing.Optional[discord.Member] = None, team: typing.Optional[str] = None):
		"""Display a fantasy roster"""

		with self.bot.db_manager.create_session() as session:
			fantasy_team = None

			# argument options
			if member:
				# search for the member's team
				user = session.execute(select(db.User).filter_by(discord_id=member.id)).scalar_one_or_none()
				if not user or not user.fantasyteam:
					return await ctx.send(f"{member.name} does not have a registered fantasy team.")
				fantasy_team = user.fantasyteam
			elif team:
				# search for specified team
				fantasy_team = session.execute(select(db.FantasyTeam).where(
					or_(
						db.FantasyTeam.name == team,
						db.FantasyTeam.abbrev == team
					)
				)).scalar_one_or_none()
				if not fantasy_team:
					return await ctx.send(f"No fantasy team found for {team}")
			else:
				# otherwise, use the author's team
				author = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
				if not author or not author.fantasyteam:
					return await ctx.send("You do not have a registered fantasy team. Use the `!register` command. Type `!help` for more information.")
				fantasy_team = author.fantasyteam

			fantasy_players = fantasy_team.fantasyplayers

			# format output
			buf = "```\n" + fantasy_team.abbrev + " / " + fantasy_team.name
			total = 0
			buf2 = ""
			for k in range(self.pos_max):
				line = add_spaces("", 4) + str(POSITIONS[k])
				for fp in fantasy_players:
					if fp.position is k:
						line += add_spaces(line, 16) + f"{fp.player.team.abbrev} {fp.player.name}"
						# update player information from results
						# TODO optimize this out maybe with caching?
						for row in fp.player.results:
							fantasy_points = self.bot.cache.retrieve(fp.player.id, row.game_id)
							if not fantasy_points:
								# game is not in cache, so perform calculation
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
		"""Show all available free agents"""

		with self.bot.db_manager.create_session() as session:
			# get all remaining players that are not drafted
			stmt = select(db.Player).where(db.Player.id.notin_(select(db.FantasyPlayer.player_id)))
			free_agents = session.scalars(stmt)

			buf = "```\nFree Agents\n"
			line = add_spaces("", 4) + "Player"
			line += add_spaces(line, 24) + "Points"
			buf += line + "\n\n"
			for player in free_agents:
				# update player information from results
				# TODO optimize this out
				for row in player.results:
					fantasy_points = self.bot.cache.retrieve(player.id, row.game_id)
					if not fantasy_points:
						# game is not in cache, so perform calculation
						fantasy_points = PointCalculator.score(row)
						self.bot.cache.store(player.id, row.game_id, fantasy_points)
				player_points = self.bot.cache.retrieve_total(player.id)
				line = add_spaces("", 4) + f"{player.team.abbrev} {player.name}"
				line += add_spaces(line, 24) + str(player_points)

				# check to ensure that the message has not exceeded discord's character limit
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
		"""Set a player's position in your team"""

		# check position is valid
		if not position.lower() in (string.lower() for string in POSITIONS.values()):
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")
		dest_pos = list(POSITIONS.keys())[list(string.lower() for string in POSITIONS.values()).index(position.lower())]
		if dest_pos >= self.pos_max:
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")

		with self.bot.db_manager.create_session() as session:
			# check that player exists
			set_player = session.execute(select(db.Player).filter_by(name=player)).scalar_one_or_none()
			if not set_player:
				return await ctx.send(f"No player was not found for \"{player}\".")
			
			# check that the player is on the user's team
			user = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
			if set_player.fantasyplayer not in user.fantasyteam.fantasyplayers:
				return await ctx.send(f"{set_player.name} is not on your roster.")

			# check if the desired position is filled
			dest_player = session.execute(select(db.FantasyPlayer).filter_by(fantasy_team_id=user.fantasy_team_id, position=dest_pos)).scalar_one_or_none()
			if dest_player:
				# swap positions
				dest_player.position = set_player.position
				set_player.fantasyplayer.position = dest_pos
			else:
				# update source player position
				set_player.fantasyplayer.position = dest_pos
			
			# verify that we do not violate the one from each team rule
			existing_teams = list()
			for curr_player in user.fantasyteam.fantasyplayers:
				if curr_player.position > 0 and curr_player.position < 6:
					if curr_player.player.team in existing_teams:
						session.rollback()
						return await ctx.send("Cannot assign player to this position due to team restriction. See !rules.")
					else:
						existing_teams.append(curr_player.player.team)

			# commit transaction and format output
			session.flush()
			session.commit()
			await ctx.invoke(self.bot.get_command('roster'))

	@commands.command()
	async def standings(self, ctx):
		"""Show the current fantasy league standings"""

		with self.bot.db_manager.create_session() as session:
			# get curret scores
			fteams = list(session.scalars(select(db.FantasyTeam)))
			for fteam in fteams:
				total = 0
				for fp in fteam.fantasyplayers:
					# don't count subs
					if fp.position < 6:
						# update player information from results
						# TODO optimize this out
						for row in fp.player.results:
							fantasy_points = self.bot.cache.retrieve(fp.player.id, row.game_id)
							if not fantasy_points:
								# game is not in cache, so perform calculation
								fantasy_points = PointCalculator.score(row)
								self.bot.cache.store(fp.player.id, row.game_id, fantasy_points)
						player_points = self.bot.cache.retrieve_total(fp.player.id)
						if fp.position == 0:
							player_points = player_points * 1.2
						total = round(total + player_points, 1)
				fteam.points = total

			sorted_teams = sorted(fteams, key=lambda k: k.points, reverse=True)

			# format output
			buf = "```\n" + "Standings\n\n"
			for fteam in sorted_teams:
				# team: (id, name, abbrev, score)
				buf += f"\t{fteam.abbrev} / {fteam.name} - {str(fteam.points)}\n"
			buf += "```"
			await ctx.send(buf)


class StatsCog(commands.Cog, name="Stats"):
	def __init__(self, bot):
		self.bot = bot

	# Cog error handler
	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Stats cog: {error}")

	@commands.command()
	async def info(self, ctx, *args: str):
		"""Get information about a player or team"""
		query_string = " ".join(args)

		with self.bot.db_manager.create_session() as session:
			# check if query_string is a team
			team = session.execute(select(db.Team).filter_by(name=query_string)).scalar_one_or_none()
			if team:
				buf = "```\n" + str(team.name)
				for player in team.players:
					buf += "\n    " + str(player.name)
				buf += "```"
				return await ctx.send(buf)

			# check if query_string is a player
			player = session.execute(select(db.Player).filter_by(name=query_string)).scalar_one_or_none()
			if player:
				for row in player.results:
					fantasy_points = self.bot.cache.retrieve(player.id, row.game_id)
					if not fantasy_points:
						# game is not in cache, so perform calculation
						fantasy_points = PointCalculator.score(row)
						self.bot.cache.store(player.id, row.game_id, fantasy_points)
					total = self.bot.cache.retrieve_total(player.id)

				# format output
				buf = f"```\n{player.name} - {str(total)}\n"
				buf += f"    Team: {player.team.name}\n"
				buf += "\n"
				buf += "    Match Results\n"
				line = add_spaces("", 8) + "Points"
				line += add_spaces(line, 16) + "ACS"
				line += add_spaces(line, 24) + "K/D/A"
				line += add_spaces(line, 34) + "Game ID\n"
				buf += line
				for row in player.results:
					line = add_spaces("", 8) + str(self.bot.cache.retrieve(player.id, row.game_id))
					line += add_spaces(line, 16) + str(row.player_acs)
					line += add_spaces(line, 24) + f"{str(row.player_kills)}/{str(row.player_deaths)}/{str(row.player_assists)}"
					line += add_spaces(line, 34) + str(row.game_id) + "\n"
					buf += line
				buf += "```"
				return await ctx.send(buf)

		await ctx.send("A team or player was not found for {}.".format(query_string))


async def setup(bot):
	await bot.add_cog(StatsCog(bot))
	await bot.add_cog(FantasyCog(bot))
	await bot.add_cog(ConfigCog(bot))
