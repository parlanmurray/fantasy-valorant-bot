
# TODO pretty print

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

	def __str__(self):
		format_str = ""
		format_str += "{}\t\t{}\t{}\t{}/{}/{}\t".format(
			self.name, 
			self.agent, 
			self.stats['acs'], 
			self.stats['kills'], 
			self.stats['deaths'],
			self.stats['assists']
			)
		if self.stats['kills'] < 10 or self.stats['deaths'] < 10 or self.stats['assists'] < 10:
			format_str += "\t"
		format_str +="{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
			self.stats['2k'],
			self.stats['3k'],
			self.stats['4k'],
			self.stats['5k'],
			self.stats['1v2'],
			self.stats['1v3'],
			self.stats['1v4'],
			self.stats['1v5'])
		return format_str

	def set_stat_int(self, key, value):
		self.stats[key] = int(value)


class Team:
	def __init__(self, name: str, won: bool, score: int):
		self.name = name
		self.players = list()
		self.won = won
		self.score = score
		self.map_pick = False

	def __str__(self):
		format_str = ""
		format_str += "{0}\t{1}".format(
			self.name,
			self.score
		)
		if self.won:
			format_str += " -- Winner"
		if self.map_pick:
			format_str += " -- Map Pick"
		format_str += "\nPlayer\t\tAgent\tACS\tK/D/A\t\t2k\t3k\t4k\t5k\t1v2\t1v3\t1v4\t1v5"
		format_str += "\n{0}\n{1}\n{2}\n{3}\n{4}\n".format(
			self.players[0],
			self.players[1],
			self.players[2],
			self.players[3],
			self.players[4]
		)
		return format_str


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
	
	def __str__(self):
		return "{}\tGame ID: {}\n\n{}\n{}".format(
			self.name, 
			self.game_id, 
			self.team1, 
			self.team2
		)

	def set_team(self, team: Team):
		if not self.team1:
			self.team1 = team
		elif not self.team2:
			self.team2 = team


class Match:
	pass
