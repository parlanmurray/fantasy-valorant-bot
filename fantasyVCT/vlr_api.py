import datetime
import re
import asyncio

import fantasyVCT.database as db

import requests
from discord.ext import tasks, commands
from sqlalchemy import select

vlr_api = "https://vlrggapi.vercel.app/{}"

class FetchCog(commands.Cog, name="Results"):
	def __init__(self, bot):
		self.bot = bot
		# self.get_results.start()

	def cog_unload(self):
		self.get_results.cancel()

	# @commands.command()
	async def update(self, ctx):
		"""Get new match results early"""
		# TODO out of date, vlr_api does not work, needs updating to sqlalchemy, uncomment command()
		r = requests.get(vlr_api.format("match/results"))
		# verify request
		if r.status_code != 200:
			ts = datetime.datetime.now()
			print(ts, "- ", str(r.status_code), "status returned from vlrggapi")
			return
		json = r.json()

		# check each game if the tournament name is registered in the event table
		for game in json['data']['segments']:
			event_info = self.bot.db_manager.query_events_from_name(game['tournament_name'])

			# allow other tasks to run
			await asyncio.sleep(5)

			if event_info:
				vlr_id = game['match_page'].split('/')[1]

				# check that the input is valid
				if not re.match("^[0-9]{5,6}$", vlr_id):
					ts = datetime.datetime.now()
					print(ts, "- ", "invalid match id ", vlr_id)
					continue

				# check that match does not exist in database
				if self.bot.db_manager.query_results_all_from_match_id(str(vlr_id)):
					continue

				await ctx.invoke(self.bot.get_command('upload'), vlr_id)

	@commands.command()
	async def upload(self, ctx, vlr_id: str):
		"""Upload a vlr.gg match"""
		# check that the input is valid
		if not re.match("^[0-9]{5,6}$", vlr_id):
			return await ctx.send("Not a valid vlr match number.")
		
		with self.bot.db_manager.create_session() as session:
			# check that match does not exist in database
			if session.scalars(select(db.Result).where(db.Result.match_id.in_([vlr_id]))):
				return await ctx.send("This match has already been uploaded.")

			# parse link
			results_scraped = self.bot.scraper.parse_match(vlr_id)
		
			# verify teams and players exist in database
			for map_scraped in results_scraped.maps:
				for team_scraped in (_map.team1, _map.team2):
					# check that teams exist in database
					team = session.execute(select(db.Team).filter_by(name=team_scraped.name)).scalar_one()
					if not team:
						# team does not exist in database
						team = db.Team(name=team_scraped.name, abbrev=team_scraped.abbrev)
						session.add(team)
					
					for player_scraped in team_scraped.players:
						# check that player exists in database
						player = session.execute(select(db.Player).filter_by(name=player_scraped.name)).scalar_one()
						if not player:
							# player does not exist in database
							player = db.Player(name=player_scraped.name)
							session.add(player)
						if not player.team:
							# player is not assigned to a team
							player.team = team

						# add result to results table
						# TODO missing actual stats here
						# TODO i want to parse directly into our db.Result class instead of the valorant.py Player class
						# for now we are ok with no stats, this is temporary
						result = db.Result(map=map_scraped.name, game_id=map_scraped.game_id, match_id=vlr_id, player_id=player.id)
						session.add(result)

			# commmit and send response
			self.bot.cache.invalidate()
			session.flush()
			session.commit()
			for map_scraped in results_scraped.maps:
				await ctx.send("```\n" + str(map_scraped) + "\n```")


	@tasks.loop(hours=1.0)
	async def get_results(self):
		r = requests.get(vlr_api.format("match/results"))

		# verify request
		if r.status_code != 200:
			ts = datetime.datetime.now()
			print(ts, "- ", str(r.status_code), "status returned from vlrggapi")
			return
		json = r.json()

		# check each game if the tournament name is registered in the event table
		for game in json['data']['segments']:
			event_info = self.bot.db_manager.query_events_from_name(game['tournament_name'])

			# allow other tasks to run
			await asyncio.sleep(5)

			if event_info:
				vlr_id = game['match_page'].split('/')[1]

				# check that the input is valid
				if not re.match("^[0-9]{5,6}$", vlr_id):
					ts = datetime.datetime.now()
					print(ts, "- ", "invalid match id ", vlr_id)
					return

				# check that match does not exist in database
				if self.bot.db_manager.query_results_all_from_match_id(str(vlr_id)):
					return

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
							self.bot.db_manager.insert_result_to_results(_map.name, _map.game_id, vlr_id, player_info[0], player, event_info[0])
							self.bot.db_manager.commit()

				self.bot.cache.invalidate()

	@get_results.before_loop
	async def before_get_results(self):
		await self.bot.wait_until_ready()


async def fetch_setup(bot):
	await bot.add_cog(FetchCog(bot))
