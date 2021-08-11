import mysql.connector


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

	def connect(self):
		self._conn = mysql.connector.connect(user=self.user, password=self.password,
											 host=self.host, database=self.database)

	def close(self):
		if self._conn:
			self._conn.close()
			self._conn = None

	def is_open(self):
		return True if self._conn else False

	def query_team_players(self, team_id):
		cursor = self._conn.cursor()

		query = """SELECT players.id, players.name FROM players 
				   INNER JOIN teams ON players.team_id = teams.id AND teams.id = %s"""
		data = (team_id)
		cursor.execute(query, data)

		results = cursor.fetchall()
		print(results)

		cursor.close()
