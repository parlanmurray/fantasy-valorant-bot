import datetime

import requests
from discord.ext import tasks, commands

vlr_api = "https://vlrggapi.herokuapp.com/{}"

class FetchCog(commands.Cog):
    def __init__(self):
        self.get_results.start()

    def cog_unload(self):
        self.get_results.cancel()

    @tasks.loop(hours=1.0)
    async def get_results(self):
        r = requests.get(vlr_api.format("match/results"))
		if json['data']['status'] != 200:
			ts = datetime.datetime.now()
			print(ts, "- ", str(json['data']['status']), " status returned from vlrggapi")
			return

		# check each game if the tournament name is registered in the event table
		# then upload if its not already present
		for game in json['data']['segments']:
			if self.db_manager.query_events_from_name(game['tournament_name']):
				match_id = game['match_page'].split('/')[1]
				if not self.db_manager.query_results_all_from_game_id(match_id):
					ctx = self.get_context()
					cmd = self.get_command('upload')
					await ctx.invoke(cmd, vlr_id=match_id)

def get_results():
	r = requests.get(vlr_api.format("match/results"))
	if r.status_code != 200:
		raise RuntimeError
	return r.json()
