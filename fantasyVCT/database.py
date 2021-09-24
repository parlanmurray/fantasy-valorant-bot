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

######################################
## players
######################################

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











