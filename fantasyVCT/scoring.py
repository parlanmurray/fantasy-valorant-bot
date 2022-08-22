from fantasyVCT.valorant import Player, add_spaces

ACS = 0.05
KILLS = 2
DEATHS = -1
ASSISTS = 0.5
KILLS2 = 1
KILLS3 = 1.5
KILLS4 = 2
KILLS5 = 2.5
CLUTCH_V2 = 3
CLUTCH_V3 = 4
CLUTCH_V4 = 5
CLUTCH_V5 = 6

class Cache:

	"""Caches scores to prevent the need for many database requests.

	Store is an outer dict, keyed by player_id as int. Value is another dict.
	Inner dict contains scores keyed by match id as int. Also contains a key -1,
	which corresponds to the total score. If the value corresponding to -1 is None,
	total score should be recalculated and stored.
	"""
	
	def __init__(self):
		self._store = dict()

	def invalidate(self):
		"""Invalidate the cache. Remove all total scores.
		"""
		for player in self._store.keys():
			scores = self._store[player]
			scores[-1] = None

	def store(self, player_id: int, key: int, value):
		"""Store a key and value in a player's store. Create the player's store
		if it does not exist already.
		
		Args:
		    player_id (int): the id of the player to associate the key and value with
		    key (int): the key to store
		    value (int): the value to store
		"""
		if not player_id in self._store:
			self._store[player_id] = {-1 : None}
		self._store[player_id][key] = value

	def retrieve(self, player_id: int, key: int = None):
		"""Retrieve a specific value or all values associated with a player id.
		
		Args:
		    player_id (int): the player id to use when searching store
		    key (int, optional): the key to retrieve a specific value
		
		Returns:
		    int/dict: either a specific value if a key is provided, or the entire store dict associated
		    	with the player id
		"""
		if not player_id in self._store:
			return None
		elif key and key in self._store[player_id]:
			return self._store[player_id][key]
		elif key:
			return None
		else:
			return self._store[player_id].copy()

	def retrieve_total(self, player_id: int):
		"""Retrieve the total of all values associated with a player id.
		If it is not up to date, calculate total.
		
		Args:
		    player_id (int): the player id to retrieve the total for
		
		Returns:
		    int: total of all values for the specified player id
		"""
		if not player_id in self._store:
			return 0

		rv = self._store[player_id][-1]
		if not rv:
			# total is not current, so perform calculation
			rv = 0
			for k,v in self._store[player_id].items():
				if k == -1:
					continue
				rv += v
			self._store[player_id][-1] = round(rv, 1)
		return round(rv, 1)


class PointCalculator:

	@staticmethod
	def get_scoring_info():
		"""
		print storing info.
		similar to __str__ or __repr__ but static
		"""
		rv = "Scoring info:\n"
		line = "ACS"
		rv += line + add_spaces(line, 20) + str(ACS) + "\n"
		line = "KILLS" 
		rv += line + add_spaces(line, 20) + str(KILLS) + "\n"
		line = "DEATHS"
		rv += line + add_spaces(line, 20) + str(DEATHS) + "\n"
		line = "ASSISTS"
		rv += line + add_spaces(line, 20) + str(ASSISTS) + "\n"
		line = "KILLS2"
		rv += line + add_spaces(line, 20) + str(KILLS2) + "\n"
		line = "KILLS3"
		rv += line + add_spaces(line, 20) + str(KILLS3) + "\n"
		line = "KILLS4"
		rv += line + add_spaces(line, 20) + str(KILLS4) + "\n"
		line = "KILLS5"
		rv += line + add_spaces(line, 20) + str(KILLS5) + "\n"
		line = "CLUTCH_V2"
		rv += line + add_spaces(line, 20) + str(CLUTCH_V2) + "\n"
		line = "CLUTCH_V3"
		rv += line + add_spaces(line, 20) + str(CLUTCH_V3) + "\n"
		line = "CLUTCH_V4"
		rv += line + add_spaces(line, 20) + str(CLUTCH_V4) + "\n"
		line = "CLUTCH_V5"
		rv += line + add_spaces(line, 20) + str(CLUTCH_V5)
		return rv

	@staticmethod
	def score(player_stats):
		"""
		player_stats retrieved from results table:
		(id, map, game_id, match_id, event_id, player_id, player_acs, player_kills, player_deaths, player_assists,
		player_2k, player_3k, player_4k, player_5k,
		player_clutch_v2, player_clutch_v3, player_clutch_v4, player_clutch_v5)
		"""
		rv = player_stats[6] * ACS
		rv += player_stats[7] * KILLS
		rv += player_stats[8] * DEATHS
		rv += player_stats[9] * ASSISTS
		rv += player_stats[10] * KILLS2
		rv += player_stats[11] * KILLS3
		rv += player_stats[12] * KILLS4
		rv += player_stats[13] * KILLS5
		rv += player_stats[14] * CLUTCH_V2
		rv += player_stats[15] * CLUTCH_V3
		rv += player_stats[16] * CLUTCH_V4
		rv += player_stats[17] * CLUTCH_V5
		return round(rv, 1)
