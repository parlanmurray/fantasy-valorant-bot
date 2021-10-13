from enum import Enum
import re
import typing

from fantasyVCT.scoring import PointCalculator

from discord.ext import commands
import discord


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
	1 : "Player1",
	2 : "Player2",
	3 : "Player3",
	4 : "Player4",
	5 : "Player5",
	6 : "Flex",
	7 : "Sub1",
	8 : "Sub2",
	9 : "Sub3",
	10 : "Sub4"
}

def add_spaces(buff, length):
	"""
	Add spaces until the buffer is at least the provided length.
	"""
	rv = ""
	while (len(buff) + len(rv)) < length:
		rv += " "
	return rv


class Test(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def hello(self, ctx):
		await ctx.send("Hello {0.name}".format(ctx.author))


class FantasyCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def register(self, ctx, team_abbrev: str, *team_name_list: str):
		team_name = " ".join(team_name_list)

		# get author's unique id
		author_id = ctx.message.author.id
		author_registered = False

		# check that user is not already registered
		user_info = self.bot.db_manager.query_users_all_from_discord_id(author_id)
		if user_info:
			author_registered = True
			if user_info[1]:
				return await ctx.send("You have already registered a team.")

		# check that team_abbrev or team_name are not taken
		if self.bot.db_manager.query_fantasy_teams_all_from_name(team_name):
			return await ctx.send("{} is taken, please choose another name.".format(team_name))
		elif self.bot.db_manager.query_fantasy_teams_all_from_abbrev(team_abbrev):
			return await ctx.send("{} is taken, please choose another abbreviation.".format(team_abbrev))

		# register user
		if not author_registered:
			self.bot.db_manager.insert_user_to_users(author_id)

		# register team
		self.bot.db_manager.insert_team_to_fantasy_teams(team_name, team_abbrev)

		# commit transaction
		self.bot.db_manager.commit()

		# register team to user
		fantasy_team_id = self.bot.db_manager.query_fantasy_teams_all_from_name(team_name)[0]
		self.bot.db_manager.update_users_fantasy_team(author_id, fantasy_team_id)
		self.bot.db_manager.commit()

		# reply
		await ctx.send("{} / {} has been registered for {}".format(team_abbrev, team_name, ctx.message.author.mention))

	@commands.command()
	async def upload(self, ctx, vlr_id: str):
		# check that the input is valid
		if not re.match("^[0-9]{5}$", vlr_id):
			return await ctx.send("Not a valid vlr match number.")

		# check that match does not exist in database
		if self.bot.db_manager.query_results_all_from_game_id(vlr_id):
			return await ctx.send("This match has already been uploaded.")
		
		# parse link
		results = self.bot.scraper.parse_match(vlr_id)

		# verify teams and players exist in database
		for _map in results.maps:
			for team in (_map.team1, _map.team2):
				# check that teams exist in database
				team_info = self.bot.db_manager.query_team_all_from_name(team.name)
				if not team_info:
					# team does not exist in database
					self.bot.db_manager.insert_team_to_teams(team.name, team.abbrev, "TEST")
					self.bot.db_manager.commit()
					team_info = self.bot.db_manager.query_team_all_from_name(team.name)

				team_id = team_info[0]

				for player in team.players:
					# check that players exist in database
					player_info = self.bot.db_manager.query_players_all_from_name(player.name)
					if not player_info:
						# player does not exist in database
						self.bot.db_manager.insert_player_to_players(player.name, team_id)
						player_info = self.bot.db_manager.query_players_all_from_name(player.name)
					elif not player_info[2] or player_info[2] != team_id:
						# player is not assigned to a team
						self.bot.db_manager.update_players_team_id(player_info[0], team_id)

					# upload data
					self.bot.db_manager.insert_result_to_results(_map.name, _map.game_id, player_info[0], player, None)
					self.bot.db_manager.commit()

		self.bot.cache.invalidate()
		for _map in results.maps:
			await ctx.send("```\n" + str(_map) + "\n```")

	@commands.command()
	async def draft(self, ctx, player_name: str):
		author_id = ctx.message.author.id

		# check status
		if not self.bot.status.is_draft_started():
			return await ctx.send("Draft has not started yet!")
		elif not self.bot.status.can_draft(author_id):
			return await ctx.send("It is not your turn yet!")

		# search for player
		player_info = self.bot.db_manager.query_players_all_from_name(player_name)
		if not player_info:
			return await ctx.send("No player was found for \"{}\"".format(player_name))

		# check that player isn't already on a team
		if self.bot.db_manager.query_fantasy_players_all_from_player_id(player_info[0]):
			return await ctx.send("{} has already been drafted to a fantasy team.".format(player_info[1]))

		# check that the user has a valorant roster
		user_info = self.bot.db_manager.query_users_all_from_discord_id(author_id)
		if not user_info:
			return await ctx.send("You are not registered. Please use the `!register` command to register. Type `!help` for more informaiton.")
		elif not user_info[1]:
			return await ctx.send("You do not have a fantasy team. Please use the `!register` command to create a fantasy team. Type `!help` for more information.")

		# find spot on roster for player
		fantasy_team_info = self.bot.db_manager.query_fantasy_teams_all_from_id(user_info[1])
		fantasy_players_info = self.bot.db_manager.query_fantasy_players_all_from_team_id(fantasy_team_info[0])
		skip_flag = False
		for i in range(1, 11):
			if skip_flag and i < 6:
				continue
			elif self.bot.db_manager.query_fantasy_players_all_from_team_id_and_position(fantasy_team_info[0], i):
				continue
			elif i < 6 and player_info[2] and self.bot.db_manager.query_fantasy_players_same_real_team(fantasy_team_info[0], player_info[2]):
				skip_flag = True
				continue

			# place player on roster
			self.bot.db_manager.insert_fantasy_player_to_fantasy_players(player_info[0], fantasy_team_info[0], i)
			self.bot.db_manager.commit()
			await ctx.invoke(self.bot.get_command('roster'))

			# update status
			if self.bot.status.is_draft_started() and not self.bot.status.is_draft_complete():
				next_drafter = self.bot.status.next()
				if next_drafter:
					await ctx.send("It is <@!{}>'s turn to draft!".format(next_drafter))
				else:
					await ctx.send("Initial draft is complete!")
			return

		return await ctx.send("You do not have a spot for this player on your roster. Use `!drop` if you want to make space. Type `!help` for more information.")

	@commands.command()
	async def drop(self, ctx, player_name: str):
		author_id = ctx.message.author.id

		# check status
		if not self.bot.status.is_draft_complete():
			return await ctx.send("Cannot drop players until initial draft is complete.")

		# search for player
		player_info = self.bot.db_manager.query_players_all_from_name(player_name)
		if not player_info:
			return await ctx.send("No player was found for \"{}\"".format(player_name))

		# check that player is on user's roster
		user_info = self.bot.db_manager.query_users_all_from_discord_id(author_id)
		fantasy_player_info = self.bot.db_manager.query_fantasy_players_all_from_player_id(player_info[0])
		if not fantasy_player_info or fantasy_player_info[2] != user_info[1]:
			return await ctx.send("No player {} found on your roster. Try the `!roster` command. Type `!help` for more information.".format(player_info[1]))

		# drop player
		self.bot.db_manager.delete_fantasy_players_from_player_id(player_info[0])
		self.bot.db_manager.commit()
		await ctx.send("{} is now a free agent!".format(player_info[1]))

	@commands.command()
	async def roster(self, ctx, member: typing.Optional[discord.Member] = None, team: typing.Optional[str] = None):
		fantasy_team_info = None
		fantasy_players = None

		# argument options
		if member:
			# search for the member's team
			user_info = self.bot.db_manager.query_users_all_from_discord_id(member.id)
			if not user_info:
				return await ctx.send(member.name + " does not have a registered fantasy team.")
			fantasy_team_info = self.bot.db_manager.query_fantasy_teams_all_from_id(user_info[1])
			if not fantasy_team_info:
				return await ctx.send(member.name + " does not have a registered fantasy team.")
			fantasy_players = self.bot.db_manager.query_fantasy_players_all_from_team_id(fantasy_team_info[0])
		elif team:
			# search for the specified team
			fantasy_team_info = self.bot.db_manager.query_fantasy_teams_all_from_either(team)
			if not fantasy_team_info:
				return await ctx.send("No fantasy team found for {}".format(team))
			fantasy_players = self.bot.db_manager.query_fantasy_players_all_from_team_id(fantasy_team_info[0])
		else:
			# otherwise, use the author's team
			user_info = self.bot.db_manager.query_users_all_from_discord_id(ctx.message.author.id)
			if not user_info:
				return await ctx.send("You do not have a registered fantasy team. Use the `!register` command. Type `!help` for more information.")
			fantasy_team_info = self.bot.db_manager.query_fantasy_teams_all_from_id(user_info[1])
			if not fantasy_team_info:
				return await ctx.send("You do not have a registered fantasy team. Use the `!register` command. Type `!help` for more information.")
			fantasy_players = self.bot.db_manager.query_fantasy_players_all_from_team_id(fantasy_team_info[0])

		# format output
		buf = "```\n" + fantasy_team_info[2] + " / " + fantasy_team_info[1]
		total = 0
		buf2 = ""
		for k in range(1, 11):
			line = add_spaces("", 4) + str(POSITIONS[k])
			for player in fantasy_players:
				if player[3] is k:
					player_id = player[1]
					player_info = self.bot.db_manager.query_players_all_from_id(player_id)
					player_team_info = self.bot.db_manager.query_team_all_from_id(player_info[2])
					line += add_spaces(line, 16) + "{} {}".format(player_team_info[2], player_info[1])
					# update player information from results
					# TODO optimize this out
					results = self.bot.db_manager.query_results_all_from_player_id(player_id)
					for row in results:
						fantasy_points = self.bot.cache.retrieve(player_id, row[2])
						if not fantasy_points:
							# game is not in cache, so perform calculation
							fantasy_points = PointCalculator.score(row)
							self.bot.cache.store(player_id, row[2], fantasy_points)
					player_points = self.bot.cache.retrieve_total(player_id)
					if k <= 6:
						total += player_points
					line += add_spaces(line, 36) + str(player_points)
					break
			buf2 += line + "\n"
			if k is 6:
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
		free_agents = self.bot.db_manager.query_players_all_not_drafted()
		buf = "```\nFree Agents\n"
		line = add_spaces("", 4) + "Player"
		line += add_spaces(line, 24) + "Points"
		buf += line + "\n\n"
		for player_info in free_agents:
			player_id = player_info[0]
			team_info = self.bot.db_manager.query_team_all_from_id(player_info[2])
			# update player information from results
			# TODO optimize this out
			results = self.bot.db_manager.query_results_all_from_player_id(player_id)
			for row in results:
				fantasy_points = self.bot.cache.retrieve(player_id, row[2])
				if not fantasy_points:
					# game is not in cache, so perform calculation
					fantasy_points = PointCalculator.score(row)
					self.bot.cache.store(player_id, row[2], fantasy_points)
			player_points = self.bot.cache.retrieve_total(player_id)
			line = add_spaces("", 4) + "{} {}".format(team_info[2], player_info[1])
			line += add_spaces(line, 24) + str(player_points)
			buf += line + "\n"
		buf += "```"
		await ctx.send(buf)

	@commands.command()
	async def set(self, ctx, player: str, position: str):
		# check position is valid
		if not position.lower() in (string.lower() for string in POSITIONS.values()):
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")
		dest_pos = list(POSITIONS.keys())[list(string.lower() for string in POSITIONS.values()).index(position.lower())]

		# check that player exists
		player_info = self.bot.db_manager.query_players_all_from_name(player)
		if not player_info:
			return await ctx.send("No player was not found for \"{}\".".format(player))

		# check that the player is on the user's team
		user_info = self.bot.db_manager.query_users_all_from_discord_id(ctx.message.author.id)
		found_flag = False
		fantasy_player_info = self.bot.db_manager.query_fantasy_players_all_from_player_id(player_info[0])
		if not fantasy_player_info:
			return await ctx.send("{} is not on your roster.".format(player_info[1]))

		# check if the desired position is filled
		dest_player = self.bot.db_manager.query_fantasy_players_all_from_team_id_and_position(user_info[1], dest_pos)
		if dest_player:
			# swap positions
			self.bot.db_manager.delete_fantasy_players_from_player_id(player_info[0])
			self.bot.db_manager.update_fantasy_players_position(dest_player[1], fantasy_player_info[3])
			self.bot.db_manager.insert_fantasy_player_to_fantasy_players(fantasy_player_info[1], fantasy_player_info[2], dest_pos)
		else:
			# update source record
			self.bot.db_manager.update_fantasy_players_position(fantasy_player_info[1], dest_pos)

		self.bot.db_manager.commit()
		await ctx.invoke(self.bot.get_command('roster'))

	@commands.command()
	async def startdraft(self, ctx):
		if self.bot.status.is_draft_complete():
			return await ctx.send("Draft is already complete.")
		elif self.bot.status.is_draft_started():
			return await ctx.send("Draft has already begun.")
		registered_users = self.bot.db_manager.query_users_discord_id()
		users_list = list()
		for user in registered_users:
			users_list.append(user[0])
		next_drafter = self.bot.status.start_draft(users_list)
		await ctx.send("It is <@!{}>'s turn!".format(next_drafter))

	@commands.command()
	async def newteam(self, ctx, url: str):
		if self.bot.status.is_draft_started():
			return await ctx.send("Cannot add additional teams/players once draft has started.")
		team_name, team_abbrev, player_names = self.bot.scraper.parse_team(url)

		# check if team exists in database
		team_info = self.bot.db_manager.query_team_all_from_name(team_name)
		if not team_info:
			# team does not exist in database
			self.bot.db_manager.insert_team_to_teams(team_name, team_abbrev, "TEST")
			self.bot.db_manager.commit()
			team_info = self.bot.db_manager.query_team_all_from_name(team_name)

		team_id = team_info[0]

		# check if players exist in database
		for player_name in player_names:
			# check that players exist in database
			player_info = self.bot.db_manager.query_players_all_from_name(player_name)
			if not player_info:
				# player does not exist in database
				self.bot.db_manager.insert_player_to_players(player_name, team_id)
				player_info = self.bot.db_manager.query_players_all_from_name(player_name)
			elif not player_info[2] or player_info[2] != team_id:
				# player is not assigned to a team
				self.bot.db_manager.update_players_team_id(player_info[0], team_id)
		self.bot.db_manager.commit()
		return await ctx.invoke(self.bot.get_command('info'), team_name)

	@commands.command()
	async def skipdraft(self, ctx):
		self.bot.status.skip_draft()

class StatsCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def info(self, ctx, *args: str):
		query_string = " ".join(args)

		# check if query_string is a team
		team_info = self.bot.db_manager.query_team_all_from_name(query_string)
		if team_info:
			players = self.bot.db_manager.query_team_players_from_id(team_info[0])
			buf = "```\n" + str(team_info[1])
			for player in players:
				buf += "\n    " + str(player[0])
			buf += "```"
			return await ctx.send(buf)

		# check if query_string is a player
		player_info = self.bot.db_manager.query_players_all_from_name(query_string)
		if player_info:
			player_id = player_info[0]
			team_info = self.bot.db_manager.query_team_all_from_id(player_info[2])
			results = self.bot.db_manager.query_results_all_from_player_id(player_id)
			# iterate through results
			for row in results:
				fantasy_points = self.bot.cache.retrieve(player_id, row[2])
				if not fantasy_points:
					# game is not in cache, so perform calculation
					fantasy_points = PointCalculator.score(row)
					self.bot.cache.store(player_id, row[2], fantasy_points)
			total = self.bot.cache.retrieve_total(player_id)

			# format output
			buf = "```\n" + player_info[1] + " - " + str(total) + "\n"
			buf += "    " + "Team: " + team_info[1] + "\n"
			buf += "\n"
			buf += "    Match Results\n"
			line = add_spaces("", 8) + "Points"
			line += add_spaces(line, 16) + "ACS"
			line += add_spaces(line, 24) + "K/D/A"
			line += add_spaces(line, 34) + "Game ID\n"
			buf += line
			for row in results:
				line = add_spaces("", 8) + str(self.bot.cache.retrieve(player_id, row[2]))
				line += add_spaces(line, 16) + str(row[5])
				line += add_spaces(line, 24) + str(row[6]) + "/" + str(row[7]) + "/" + str(row[8])
				line += add_spaces(line, 34) + str(row[2]) + "\n"
				buf += line
			buf += "```"
			return await ctx.send(buf)

		await ctx.send("A team or player was not found for {}.".format(query_string))



