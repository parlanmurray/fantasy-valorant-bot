from fantasyVCT.valorant import Player

class Cache:

	"""Caches scores to prevent the need for many database requests.

	Store is an outer dict, keyed by player_id as int. Value is another dict.
	Inner dict contains scores keyed by match id as int. Also contains a key -1,
	which corresponds to the total score. If the value corresponding to -1 is None,
	total score should be recalculated and stored.
	"""
	
	def __init__(self):
		self.store = dict()

	def invalidate(self):
		"""Invalidate the cache. Remove all total scores.
		"""
		for player in self.store.keys():
			scores = self.store[player]
			scores[-1] = None

	def store(self, player_id: int, key: int, value):
		"""Store a key and value in a player's store. Create the player's store
		if it does not exist already.
		
		Args:
		    player_id (int): the id of the player to associate the key and value with
		    key (int): the key to store
		    value (int): the value to store
		"""
		if not player_id in self.store:
			self.store[player_id] = {-1 : None}
		self.store[player_id][key] = value

	def retrieve(self, player_id: int, key: int = None):
		"""Retrieve a specific value or all values associated with a player id.
		
		Args:
		    player_id (int): the player id to use when searching store
		    key (int, optional): the key to retrieve a specific value
		
		Returns:
		    int/dict: either a specific value if a key is provided, or the entire store dict associated
		    	with the player id
		"""
		if key:
			return self.store[player_id][key]
		else:
			return self.store[player_id].copy()

class PointCalculator:
	
	@staticmethod
	def score(player: Player):
		raise NotImplementedError
