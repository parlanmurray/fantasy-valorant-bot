from enum import Enum
from copy import deepcopy


def add_spaces(buff, length):
	"""
	Add spaces until the buffer is at least the provided length.
	"""
	rv = ""
	while (len(buff) + len(rv)) < length:
		rv += " "
	return rv


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
		line = self.name
		line += add_spaces(line, 20)
		line += self.agent
		line += add_spaces(line, 40)
		line += str(self.stats['acs'])
		line += add_spaces(line, 50)
		line += str(self.stats['kills']) + '/' + str(self.stats['deaths']) + '/' + str(self.stats['assists'])
		line += add_spaces(line, 80)
		line += str(self.stats['2k'])
		line += add_spaces(line, 90)
		line += str(self.stats['3k'])
		line += add_spaces(line, 100)
		line += str(self.stats['4k'])
		line += add_spaces(line, 110)
		line += str(self.stats['5k'])
		line += add_spaces(line, 120)
		line += str(self.stats['1v2'])
		line += add_spaces(line, 130)
		line += str(self.stats['1v3'])
		line += add_spaces(line, 140)
		line += str(self.stats['1v4'])
		line += add_spaces(line, 150)
		line += str(self.stats['1v5'])
		return line

	def _combine(self, other):
		"""Combine two Players, mutating self with other's information.
		ASSUME THAT SELF IS SUMMARY TAB INFORMATION, AND CAN BE MODIFIED.
		
		Args:
		    other (Player): the Player to integrate information from
		
		Raises:
		    ValueError: if other is not the same player as self
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
	def __init__(self, name: str, won: bool = False, score: int = 0, abbrev: str = None):
		self.name = name
		self.abbrev = abbrev
		self.players = list()
		self.won = won
		self.score = score
		self.map_pick = False

	def __str__(self):
		format_str = ""
		format_str += self.abbrev + " / " + self.name
		format_str += add_spaces(format_str, 30)
		format_str += str(self.score)
		if self.won:
			format_str += " -- Winner"
		if self.map_pick:
			format_str += " -- Map Pick"
		line = "Player"
		line += add_spaces(line, 20)
		line += "Agent"
		line += add_spaces(line, 40)
		line += "ACS"
		line += add_spaces(line, 50)
		line += "K/D/A"
		line += add_spaces(line, 80)
		line += "2k"
		line += add_spaces(line, 90)
		line += "3k"
		line += add_spaces(line, 100)
		line += "4k"
		line += add_spaces(line, 110)
		line += "5k"
		line += add_spaces(line, 120)
		line += "1v2"
		line += add_spaces(line, 130)
		line += "1v3"
		line += add_spaces(line, 140)
		line += "1v4"
		line += add_spaces(line, 150)
		line += "1v5"
		format_str += "\n" + line
		format_str += "\n{0}\n{1}\n{2}\n{3}\n{4}\n".format(
			self.players[0],
			self.players[1],
			self.players[2],
			self.players[3],
			self.players[4]
		)
		return format_str

	def _combine(self, other):
		"""Combine two Teams, mutating self with other's information.
		ASSUME THAT SELF IS SUMMARY TAB INFORMATION, AND CAN BE MODIFIED.
		
		Args:
		    other (Team): the Team to integrate information from
		
		Raises:
		    ValueError: if a corresponding player is not found in other
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

	def set_map_pick(self):
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
		"""Combine two Maps, mutating self with other's information.
		ASSUME THAT SELF IS SUMMARY TAB INFORMATION, AND CAN BE MODIFIED.
		
		Args:
		    other (Map): the Map to integrate information from
		
		Raises:
		    ValueError: if map ids do not match, or if teams do not match
		"""
		# ensure that game_id is the same
		if self.game_id != other.game_id:
			raise ValueError("Cannot combine different maps. {} {}".format(self.game_id, other.game_id))

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
		rv = "Match ID: {}\n".format(self.match_id)
		for map_ in self.maps:
			rv += "----------\n\n" + str(map_)

		return rv

	def combine(self, other):
		"""Combine two Matches into a new Match object.
		
		Args:
		    other (Match): a Match to combine information from
		
		Returns:
		    Match: a new Match with information from both self and other
		
		Raises:
		    ValueError: if match IDs are different, or if self/other are not 
		    	correct Tabs
		"""
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
