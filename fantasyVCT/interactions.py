from enum import Enum
import re

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


class FantasyCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def register(self, ctx, team_abbrev: str, team_name: str):
		# get author's unique id
		author_id = ctx.message.author.id
		author_registered = False

		# check that user is not already registered
		user_info = self.bot.db_manager.query_users_all_from_discord_id(author_id)
		if user_info:
			author_registered = True
		elif user_info[1]:
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
					elif not player_info[2]:
						# player is not assigned to a team
						self.bot.db_manager.update_players_team_id(player_info[0], team_id)
					self.bot.db_manager.commit()

					# upload data
					self.bot.db_manager.insert_result_to_results(_map.name, _map.game_id, player_info[0], player, None)

		await ctx.send("```\n" + str(results) + "\n```")


class StatsCog(commands.Cog):
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
			buf = "```\n{}:".format(team_name)
			for row in rv:
				buf += "\n\t" + row[0]
			buf += "```"
			await ctx.send(buf)
		elif cat_type is Category.PLAYER:
			pass
