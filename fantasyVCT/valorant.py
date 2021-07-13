
# feel free to modify as needed
stats_list = ['acs',
'deaths',
'assists',
'kills',
'2k',
'3k',
'4k',
'5k',
'1v2']


class Player:
	def __init__(self, name: str):
		self.name = name
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

class Team:
	def __init__(self, name: str):
		self.name = name
		self.players = list()

	def add_player(self, player: Player):
		self.players.append(player)

class Map:
	def __init__(self, map_name: str, map_number: int, was_played: bool):
		self.name = map_name
		self.number = map_number
		self.was_played = was_played
		self.team1 = None
		self.team2 = None

	def set_team(self, team: Team):
		if not self.team1:
			self.team1 = team
		elif not self.team2:
			self.team2 = team
