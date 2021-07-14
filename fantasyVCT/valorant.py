
class Player:
	def __init__(self, name: str, agent: str):
		self.name = name
		self.agent = agent
		self.stats = {
		'acs': 0,
		'deaths': 0,
		'assists': 0,
		'kills': 0,
		'2k': 0,
		'3k': 0,
		'4k': 0,
		'5k': 0,
		'1v2': 0,
		'1v3': 0,
		'1v4': 0,
		'1v5': 0
		}

	def set_stat_int(self, key, value):
		self.stats[key] = int(value)


class Team:
	def __init__(self, name: str, won: bool, score: int):
		self.name = name
		self.players = list()
		self.won = won
		self.score = score
		self.map_pick = False

	def add_player(self, player: Player):
		self.players.append(player)

	def map_pick(self):
		self.map_pick = True


class Map:
	def __init__(self, map_name: str, game_id: int):
		self.name = map_name
		self.game_id = game_id
		self.team1 = None
		self.team2 = None

	def set_team(self, team: Team):
		if not self.team1:
			self.team1 = team
		elif not self.team2:
			self.team2 = team


class Match:
	pass
