
# feel free to modify as needed

class Player:
	def __init__(self, name: str):
		self.name = name
		self.kills = 0
		self.deaths = 0
		self.assists = 0
		self.acs = 0
		self.2K = 0
		self.3K = 0
		self.4K = 0
		self.5K = 0
		self.1v1 = 0
		self.1v2 = 0
		self.1v3 = 0
		self.1v4 = 0
		self.1v5 = 0
		# TODO and so on

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

