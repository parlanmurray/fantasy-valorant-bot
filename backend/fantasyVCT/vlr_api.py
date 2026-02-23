import datetime
import re
import asyncio

import fantasyVCT.database as db
from fantasyVCT.matchup import compute_weekly_score

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

	# Cog error handler
	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Fetch cog: {error}")

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
			if session.scalars(select(db.Result).filter_by(match_id=vlr_id)).first():
				return await ctx.send("This match has already been uploaded.")

			# parse link; also grab the raw soup for week extraction
			match_url = f"https://vlr.gg/{vlr_id}"
			match_soup = self.bot.scraper.scrape_url(match_url)
			week_number = self.bot.scraper.parse_week_number(match_soup)

			# resolve week_id from active season
			week_id = None
			if week_number is not None:
				active_season = session.scalars(
					select(db.Season).where(db.Season.is_active == True)
				).first()
				if active_season:
					week = session.scalars(
						select(db.Week).where(
							db.Week.season_id == active_season.id,
							db.Week.week_number == week_number
						)
					).first()
					if week:
						week_id = week.id

			results_scraped = self.bot.scraper.parse_match(vlr_id)

			# verify teams and players exist in database
			inserted_team_ids = set()
			for map_scraped in results_scraped.maps:

				await ctx.send("```\n" + str(map_scraped) + "\n```")

				for team_scraped in (map_scraped.team1, map_scraped.team2):
					team = session.execute(select(db.Team).filter_by(name=team_scraped.name)).scalar_one_or_none()
					if not team:
						team = db.Team(name=team_scraped.name, abbrev=team_scraped.abbrev)
						session.add(team)
						session.flush()

					for player_scraped in team_scraped.players:
						player = session.execute(select(db.Player).filter_by(name=player_scraped.name)).scalar_one_or_none()
						if not player:
							player = db.Player(name=player_scraped.name)
							session.add(player)
							session.flush()

						if not player.team:
							player.team = team

						result = player_scraped.results[0]
						result.player = player
						result.week_id = week_id
						session.add(result)

						# track which fantasy teams have players affected
						if player.fantasyplayer:
							ft_id = player.fantasyplayer.fantasy_team_id
							if ft_id:
								inserted_team_ids.add(ft_id)
					session.flush()

			self.bot.cache.invalidate()
			session.commit()

			# Show live matchup scores if we tagged a week
			if week_id is not None:
				await self._show_affected_matchups(ctx, week_id, inserted_team_ids, session)

	async def _show_affected_matchups(self, ctx, week_id: int, affected_team_ids: set, session):
		"""After upload, display live scores for matchups involving affected teams."""
		if not affected_team_ids:
			return
		matchups = session.scalars(
			select(db.Matchup).where(
				db.Matchup.week_id == week_id,
				(db.Matchup.home_team_id.in_(affected_team_ids)) |
				(db.Matchup.away_team_id.in_(affected_team_ids))
			)
		).all()

		seen = set()
		for m in matchups:
			if m.id in seen:
				continue
			seen.add(m.id)
			home_score = compute_weekly_score(m.home_team_id, week_id, session)
			away_score = compute_weekly_score(m.away_team_id, week_id, session) if m.away_team_id else 0.0
			home_label = m.home_team.abbrev if m.home_team else "?"
			away_label = m.away_team.abbrev if m.away_team else "Ghost"
			week = session.get(db.Week, week_id)
			week_num = week.week_number if week else "?"
			await ctx.send(f"Week {week_num}: **{home_label}** {home_score} — {away_score} **{away_label}**")


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
