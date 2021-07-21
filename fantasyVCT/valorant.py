from enum import Enum
from copy import deepcopy


class Tab(Enum):
	SUMMARY = 1
	PERFORMANCE = 2
	COMBINED = 3


class Player:
	def __init__(self, name: str, agent: str=""):
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

	def _combine(self, other):
		"""Summary

		ASSUME THAT SELF IS SUMMARY TAB INFORMATION, AND CAN BE MODIFIED.
		
		Args:
		    other (Player): Description
		"""
		# ensure that player names are the same
		if self.name != other.name:
			raise ValueError("Cannot combine different players. {} {}".format(self.name, other.name))

		# retrieve missing stats from other
		for k, v in self.stats.items():
			if v == 0:
				self.stats[k] = other.stats[k]

	def set_stat_int(self, key: str, value):
		if key in self.stats.keys():
			self.stats[key] = int(value)


class Team:
	def __init__(self, name: str, won: bool = False, score: int = 0):
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

	def _combine(self, other):
		"""
		ASSUME THAT SELF IS SUMMARY TAB INFORMATION, AND CAN BE MODIFIED.
		"""
		# ASSUME THAT TEAMS ARE THE SAME

		# combine players
		for self_player in self.players:
			found = False
			for other_player in other.players:
				try:
					self_player._combine(other_player)
					found = True
					break
				except ValueError:
					continue

			if not found:
				raise ValueError("Corresponding player not found for {} in \n{}.".format(self_player.name, str(other)))

	def add_player(self, player: Player):
		self.players.append(player)

	def map_pick(self):
		self.map_pick = True


class Map:
	def __init__(self, game_id: int, name: str = None):
		self.name = name
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

	def _combine(self, other):
		"""
		ASSUME THAT SELF IS SUMMARY TAB INFORMATION, AND CAN BE MODIFIED.
		"""
		# ensure that game_id is the same
		if self.game_id != other.game_id:
			raise ValueError("Cannot combine maps. {} {}".format(self.game_id, other.game_id))

		# combine teams
		try:
			self.team1._combine(other.team1)
			self.team2._combine(other.team2)
		except ValueError as ve:
			raise ValueError("Teams do not match. " + str(ve))

	def set_team(self, team: Team):
		if not self.team1:
			self.team1 = team
		elif not self.team2:
			self.team2 = team


class Match:
	def __init__(self, match_id: int, tab: Tab):
		self.maps = list()
		self.match_id = match_id
		self.tab = tab

	def __str__(self):
		rv = "Match ID: {}\n".format(match_id)
		for map_ in self.maps:
			rv += "----------\n\n" + str(map_)

		return rv

	def combine(self, other):
		# ensure that match_id values are the same
		if self.match_id != other.match_id:
			raise ValueError("Cannot combine different matches. {} {}".format(self.match_id, self.match_id))

		# ensure that self is a SUMMARY and other is PERFORMANCE
		if self.tab != Tab.SUMMARY and other.tab == Tab.SUMMARY:
			return other.combine(self)
		elif self.tab == other.tab:
			raise ValueError("Each match must contain different tab information.")
		elif self.tab == Tab.COMBINED or other.tab == Tab.COMBINED:
			raise ValueError("Match cannot be of type COMBINED.")

		match_copy = deepcopy(self)
		match_copy.tab = Tab.COMBINED

		# combine maps
		for copy_map in match_copy.maps:
			found = False
			for other_map in other.maps:
				try:
					copy_map._combine(other_map)
					found = True
					break
				except ValueError:
					continue

			if not found:
				raise ValueError("Corresponding map not found for map {}.".format(copy_map.game_id))

		return match_copy

	def add_map(self, map):
		self.maps.append(map)
