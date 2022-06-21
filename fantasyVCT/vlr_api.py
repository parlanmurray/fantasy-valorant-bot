import datetime
import re

import requests
from discord.ext import tasks, commands

vlr_api = "https://vlrggapi.herokuapp.com/{}"

class FetchCog(commands.Cog):
    def __init__(self, bot):
    	self.bot = bot
        self.get_results.start()

    def cog_unload(self):
        self.get_results.cancel()

    @tasks.loop(hours=1.0)
    async def get_results(self):
        r = requests.get(vlr_api.format("match/results"))

        # check for 200 status code
		if json['data']['status'] != 200:
			ts = datetime.datetime.now()
			print(ts, "- ", str(json['data']['status']), " status returned from vlrggapi")
			return

		# check each game if the tournament name is registered in the event table
		for game in json['data']['segments']:
			if self.bot.db_manager.query_events_from_name(game['tournament_name']):
				vlr_id = game['match_page'].split('/')[1]

				# check that the input is valid
				if not re.match("^[0-9]{5}$", vlr_id):
					ts = datetime.datetime.now()
					print(ts, "- ", "invalid match id ", vlr_id)
					return

				# check that match does not exist in database
				if self.bot.db_manager.query_results_all_from_game_id(vlr_id):
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
							self.bot.db_manager.insert_result_to_results(_map.name, _map.game_id, player_info[0], player, None)
							self.bot.db_manager.commit()

				self.bot.cache.invalidate()
