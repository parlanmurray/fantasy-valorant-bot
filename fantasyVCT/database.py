from fantasyVCT.valorant import Player

import mysql.connector


def query_precheck(func):
	def wrapper(*args):
		if args[0].is_open():
			return func(*args)
		else:
			raise RuntimeError("Database connection is not open.")
	return wrapper


class DatabaseManager:
	def __init__(self, user, password, database, host = "127.0.0.1"):
		self.user = user
		self.password = password
		self.database = database
		self.host = host
		self._conn = None

	def __del__(self):
		# if connection is open, close it
		if self._conn:
			self.close()

	def open(self):
		if self.is_open():
			return
		self._conn = mysql.connector.connect(user=self.user, password=self.password,
											 host=self.host, database=self.database)

	def close(self):
		if self._conn:
			self._conn.close()
			self._conn = None

	def is_open(self):
		return True if self._conn else False

	def commit(self):
		self._conn.commit()

	def rollback(self):
		self._conn.rollback()

######################################
## teams
######################################

	@query_precheck
	def insert_team_to_teams(self, team_name, team_abbrev, region=None):
		"""
		Insert a team into the teams table.
		"""
		cursor = self._conn.cursor()

		query = """INSERT INTO teams (name, abbrev, region) VALUES (%s, %s, %s)"""
		data = (team_name, team_abbrev, region)
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def query_team_all_from_name(self, team_name):
		"""
		Returns:
		(team_id, team_name, team_abbrev, team_region)
		"""
		cursor = self._conn.cursor()

		query = """SELECT * FROM teams WHERE teams.name = %s OR teams.abbrev = %s"""
		data = (team_name, team_name)
		cursor.execute(query, data)
		row = cursor.fetchone()
		cursor.close()

		return row

	@query_precheck
	def query_team_all_from_id(self, team_id):
		"""
		Returns:
		(team_id, team_name, team_abbrev, team_region)
		"""
		cursor = self._conn.cursor()

		query = """SELECT * FROM teams WHERE teams.id = %s"""
		data = (team_name, team_id)
		cursor.execute(query, data)
		row = cursor.fetchone()
		cursor.close()

		return row

	@query_precheck
	def query_team_players_from_name(self, team_name):
		"""
		Returns:
		[(player_name, ), ...]
		"""
		cursor = self._conn.cursor()

		query = """SELECT players.name FROM players 
		INNER JOIN teams ON players.team_id = teams.id 
		WHERE teams.id in 
		(SELECT teams.id FROM teams WHERE teams.name = %s OR teams.abbrev = %s)"""
		data = (team_name, team_name)
		cursor.execute(query, data)
		results = cursor.fetchall()
		cursor.close()

		return results

	@query_precheck
	def query_team_players_from_id(self, team_id):
		"""
		Returns:
		[(player_name, ), ...]
		"""
		cursor = self._conn.cursor()

		query = """SELECT players.name FROM players 
		INNER JOIN teams ON players.team_id = teams.id WHERE teams.id = %s"""
		data = (team_id, )
		cursor.execute(query, data)
		results = cursor.fetchall()
		cursor.close()

		return results

######################################
## players
######################################

	@query_precheck
	def insert_player_to_players(self, player_name, player_team_id = None):
		"""
		Create record for a player in the players table.
		"""
		cursor = self._conn.cursor()

		query = """INSERT INTO players (name, team_id) VALUES (%s, %s)"""
		data = (player_name, player_team_id)
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def update_players_team_id(self, player_id, team_id):
		"""
		Assign a team to a player.
		"""
		cursor = self._conn.cursor()
		query = """UPDATE players SET team_id = %s WHERE id = %s"""
		data = (team_id, player_id)
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def query_players_all_from_name(self, player_name):
		"""
		Returns:
		(players.id, players.name, players.team_id)
		"""
		cursor = self._conn.cursor()
		query = """SELECT * FROM players WHERE players.name = %s"""
		data = (player_name, )
		cursor.execute(query, data)
		results = cursor.fetchone()
		cursor.close()

		return results

######################################
## results
######################################

	@query_precheck
	def insert_result_to_results(self, map_name, game_id, player_id, player: Player, event_id = None):
		"""
		Args:
		    map_name (str): the name of the map played
		    game_id (int): the id of the game
		    player_id (int): the player's database ID
		    player (Player): a Player containing information for the database
		    event_id (int, optional): the id of the event
		"""
		cursor = self._conn.cursor()
		query = """INSERT INTO results 
		(map, game_id, event_id, player_id, player_acs, player_kills, player_deaths, 
		player_assists, player_2k, player_3k, player_4k, player_5k, 
		player_clutch_v2, player_clutch_v3, player_clutch_v4, player_clutch_v5) 
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
		data = (map_name, game_id, event_id, player_id, player.stats['acs'], player.stats['kills'], 
			player.stats['deaths'], player.stats['assists'], player.stats['2k'], player.stats['3k'],
			player.stats['4k'], player.stats['5k'], player.stats['1v2'], player.stats['1v3'],
			player.stats['1v4'], player.stats['1v5'])
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def query_results_all_from_game_id(self, game_id):
		"""
		Returns:
		[(id, map, game_id, event_id, player_id, player_acs, player_kills, player_deaths, player_assists,
		player_2k, player_3k, player_4k, player_5k,
		player_clutch_v2, player_clutch_v3, player_clutch_v4, player_clutch_v5), ...]
		"""
		cursor = self._conn.cursor()
		query = """SELECT * FROM results WHERE game_id = %s"""
		data = (game_id, )
		cursor.execute(query, data)
		results = cursor.fetchall()
		cursor.close()

		return results

	@query_precheck
	def query_results_all_from_player_id(self, player_id):
		"""
		[(id, map, game_id, event_id, player_id, player_acs, player_kills, player_deaths, player_assists,
		player_2k, player_3k, player_4k, player_5k,
		player_clutch_v2, player_clutch_v3, player_clutch_v4, player_clutch_v5), ...]
		"""
		cursor = self._conn.cursor()
		query = """SELECT * FROM results WHERE player_id = %s"""
		data = (player_id, )
		cursor.execute(query, data)
		results = cursor.fetchall()
		cursor.close()

		return results


######################################
## users
######################################

	@query_precheck
	def insert_user_to_users(self, discord_id):
		"""
		Register a user into the users table.
		"""
		cursor = self._conn.cursor()

		query = """INSERT INTO users (discord_id) VALUES (%s)"""
		data = (discord_id, )
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def update_users_fantasy_team(self, discord_id, fantasy_team_id):
		"""
		Register a fantasy team with a user in users.
		"""
		cursor = self._conn.cursor()

		query = """UPDATE users SET fantasy_team_id = %s WHERE discord_id = %s"""
		data = (fantasy_team_id, discord_id)
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def query_users_all_from_discord_id(self, discord_id):
		"""
		Returns:
		(users.discord_id, users.fantasy_team_id) or None
		"""
		cursor = self._conn.cursor()

		query = """SELECT users.discord_id, users.fantasy_team_id FROM users WHERE users.discord_id = %s"""
		data = (discord_id, )
		cursor.execute(query, data)
		row = cursor.fetchone()
		cursor.close()

		return row

######################################
## fantasy_teams
######################################

	@query_precheck
	def insert_team_to_fantasy_teams(self, team_name, team_abbrev):
		"""
		Create a fantasy team.
		"""
		cursor = self._conn.cursor()

		query = """INSERT INTO fantasy_teams (name, abbrev) VALUES (%s, %s)"""
		data = (team_name, team_abbrev)
		cursor.execute(query, data)
		cursor.close()

	@query_precheck
	def query_fantasy_teams_all_from_name(self, team_name):
		"""
		Returns:
		(id, name, abbrev, player1, player2, player3, player4, player5, flex, sub1, sub2, sub3, sub4) or None
		"""
		cursor = self._conn.cursor()

		query = """SELECT * FROM fantasy_teams WHERE name = %s"""
		data = (team_name, )
		cursor.execute(query, data)
		row = cursor.fetchone()
		cursor.close()

		return row

	@query_precheck
	def query_fantasy_teams_all_from_abbrev(self, team_abbrev):
		"""
		Returns:
		(id, name, abbrev, player1, player2, player3, player4, player5, flex, sub1, sub2, sub3, sub4) or None
		"""
		cursor = self._conn.cursor()

		query = """SELECT * FROM fantasy_teams WHERE abbrev = %s"""
		data = (team_abbrev, )
		cursor.execute(query, data)
		row = cursor.fetchone()
		cursor.close()

		return row











