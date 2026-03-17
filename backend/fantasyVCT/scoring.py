from fantasyVCT.database import Result, add_spaces

ACS = 0.03
KILLS = 1.5
DEATHS = -1
ASSISTS = 0.5
FK = 1.0
KILLS2 = 2
KILLS3 = 4
KILLS4 = 7
KILLS5 = 10
CLUTCH_V2 = 8
CLUTCH_V3 = 12
CLUTCH_V4 = 16
CLUTCH_V5 = 20

# Role bonus weights (calibrated 2026-03-16, role_calibration_v3.py)
ROLE_IGL_WIN = 8.5
ROLE_DUELIST_FK = 2.0        # total FK weight = 1.0 (base) + 2.0
ROLE_INITIATOR_ASSIST = 1.0  # total assist weight = 0.5 + 1.0
ROLE_CONTROLLER_ASSIST = 0.65
ROLE_CONTROLLER_SURVIVAL = 0.35
ROLE_SENTINEL_DEATH_SAVE = 0.40  # penalty -0.60 instead of -1.0

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
		self._store[player_id][-1] = None

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
		rv += line + add_spaces(line, 20) + str(CLUTCH_V5) + "\n"
		line = "FK"
		rv += line + add_spaces(line, 20) + str(FK)
		return rv

	@staticmethod
	def score(player_stats: Result):
		"""
		player_stats retrieved from results table:
		(id, map, game_id, match_id, event_id, player_id, player_acs, player_kills, player_deaths, player_assists,
		player_2k, player_3k, player_4k, player_5k,
		player_clutch_v2, player_clutch_v3, player_clutch_v4, player_clutch_v5, player_fk)
		"""
		rv = player_stats.player_acs * ACS
		rv += player_stats.player_kills * KILLS
		rv += player_stats.player_deaths * DEATHS
		rv += player_stats.player_assists * ASSISTS
		rv += player_stats.player_2k * KILLS2
		rv += player_stats.player_3k * KILLS3
		rv += player_stats.player_4k * KILLS4
		rv += player_stats.player_5k * KILLS5
		rv += player_stats.player_clutch_v2 * CLUTCH_V2
		rv += player_stats.player_clutch_v3 * CLUTCH_V3
		rv += player_stats.player_clutch_v4 * CLUTCH_V4
		rv += player_stats.player_clutch_v5 * CLUTCH_V5
		rv += (player_stats.player_fk or 0) * FK
		return round(rv, 1)

	@staticmethod
	def role_bonus(player_stats: Result, role: str) -> float:
		"""Return the role-specific bonus points for a single result.

		Role bonuses are additive on top of the base score and are only
		applied when the player is assigned to that role slot.
		Flex and Sub slots return 0.
		"""
		r = role.lower()
		if r == 'igl':
			return ROLE_IGL_WIN if player_stats.team_won else 0.0
		elif r == 'duelist':
			return (player_stats.player_fk or 0) * ROLE_DUELIST_FK
		elif r == 'initiator':
			return player_stats.player_assists * ROLE_INITIATOR_ASSIST
		elif r == 'controller':
			survived = (player_stats.rounds_played or 0) - player_stats.player_deaths
			return (player_stats.player_assists * ROLE_CONTROLLER_ASSIST
					+ max(0, survived) * ROLE_CONTROLLER_SURVIVAL)
		elif r == 'sentinel':
			return player_stats.player_deaths * ROLE_SENTINEL_DEATH_SAVE
		return 0.0
