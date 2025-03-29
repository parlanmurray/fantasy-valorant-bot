from enum import Enum
from typing import List
import urllib

from sqlalchemy import create_engine
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
	pass


class DatabaseManager:
	def __init__(self, _type, user, password, database, host = "localhost", port = 3306):
		self.user = user
		self.password = urllib.parse.quote(password)
		self.database = database
		self.host = host
		self.port = port
		self.type = _type
		self.uri_string = f"{self.type}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
		# "mysql://<user>:<password>@localhost/FantasyValProd"
		self._engine = create_engine(self.uri_string, pool_pre_ping=True)

	def connect(self):
		"""
		Caller is repsonsible for Connection object.
		"""
		return self._engine.connect()

	def create_session(self, autoflush=False):
		"""
		Caller is responsible for Session object.
		"""

		return Session(self._engine, autoflush=autoflush)


######################################
## Mapped Classes
######################################

class Team(Base):
	__tablename__ = "teams"

	# mapped fields
	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False)
	abbrev: Mapped[str] = mapped_column(String(10), nullable=False)
	region: Mapped[str] = mapped_column(String[10])

	# relationship fields
	players: Mapped[List["Player"]] = relationship(back_populates="team")

	# other fields
	won: bool = False
	score: int = 0
	map_pick: bool = False

	def __repr__(self) -> str:
		return f"Team(id={self.id!r}, name={self.name!r}, abbrev={self.abbrev!r}, region={self.region!r})"

	def __str__(self) -> str:
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
	
	def get_player(self, name: str):
		for player in self.players:
			if player.name == name:
				return player
		return None


class Player(Base):
	__tablename__ = "players"

	# mapped fields
	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False)
	team_id = mapped_column(ForeignKey("teams.id"))
	
	# relationship fields
	team: Mapped[Team] = relationship(back_populates="players")
	results: Mapped[List["Result"]] = relationship(back_populates="player")
	fantasyplayer: Mapped["FantasyPlayer"] = relationship(back_populates="player")

	def __repr__(self) -> str:
		return f"Player(id={self.id!r}, name={self.name!r}, team_id={self.team_id!r})"

	def __str__(self) -> str:
		line = ""
		for result in self.results:
			line += self.name
			line += add_spaces(line, 20)
			line += str(result)
			if len(self.results) > 1:
				line += "\n"
		return line


class Event(Base):
	__tablename__ = "events"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(80), nullable=False)

	def __repr__(self) -> str:
		return f"Event(id={self.id!r}, name={self.name!r})"


class Result(Base):
	__tablename__ = "results"

	# mapped fields
	id: Mapped[int] = mapped_column(primary_key=True)
	map: Mapped[str] = mapped_column(String(20), nullable=False)
	game_id: Mapped[int] = mapped_column(nullable=False)
	match_id: Mapped[int] = mapped_column(nullable=False)
	event_id: Mapped[int]
	player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
	player_acs: Mapped[float]
	player_kills: Mapped[int]
	player_deaths: Mapped[int]
	player_assists: Mapped[int]
	player_2k: Mapped[int]
	player_3k: Mapped[int]
	player_4k: Mapped[int]
	player_5k: Mapped[int]
	player_clutch_v2: Mapped[int]
	player_clutch_v3: Mapped[int]
	player_clutch_v4: Mapped[int]
	player_clutch_v5: Mapped[int]
	agent: Mapped[str] = mapped_column(String[20])

	# relationship fields
	player: Mapped[Player] = relationship(back_populates="results")

	def __repr__(self) -> str:
		return (
			f"Result(id={self.id!r}, map={self.map!r}, game_id={self.game_id!r}, "
			f"match_id={self.match_id!r}, event_id={self.event_id!r}, player_id={self.player_id!r})"
			# TODO more fields?
		)

	def __str__(self) -> str:
		line = self.agent
		line += add_spaces(line, 20)
		line += str(self.player_acs)
		line += add_spaces(line, 30)
		line += f"{self.player_kills}/{self.player_deaths}/{self.player_assists}"
		line += add_spaces(line, 60)
		line += str(self.player_2k)
		line += add_spaces(line, 70)
		line += str(self.player_3k)
		line += add_spaces(line, 80)
		line += str(self.player_4k)
		line += add_spaces(line, 90)
		line += str(self.player_5k)
		line += add_spaces(line, 100)
		line += str(self.player_clutch_v2)
		line += add_spaces(line, 110)
		line += str(self.player_clutch_v3)
		line += add_spaces(line, 120)
		line += str(self.player_clutch_v4)
		line += add_spaces(line, 130)
		line += str(self.player_clutch_v5)
		return line
	

class FantasyTeam(Base):
	__tablename__ = "fantasy_teams"

	points: int = 0

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False)
	abbrev: Mapped[str] = mapped_column(String(10), nullable=False)

	user: Mapped["User"] = relationship(back_populates="fantasyteam")
	fantasyplayers: Mapped[List["FantasyPlayer"]] = relationship(back_populates="fantasyteam")

	def __repr__(self) -> str:
		return f"FantasyTeam(id={self.id!r}, name={self.name!r}, abbrev={self.abbrev!r})"


class User(Base):
	__tablename__ = "users"

	discord_id: Mapped[str] = mapped_column(String(18), primary_key=True)
	fantasy_team_id = mapped_column(ForeignKey("fantasy_teams.id"))

	fantasyteam: Mapped[FantasyTeam] = relationship(back_populates="user")

	def __repr__(self) -> str:
		return f"User(discord_id={self.discord_id!r}, fantasy_team_id={self.fantasy_team_id!r})"


class Position(Base):
	__tablename__ = "positions"

	id: Mapped[int] = mapped_column(primary_key=True)
	position: Mapped[str] = mapped_column(String(20), nullable=False)

	def __repr__(self) -> str:
		return f"Position(position={self.position!r})"


class FantasyPlayer(Base):
	__tablename__ = "fantasy_players"

	id: Mapped[int] = mapped_column(primary_key=True)
	player_id = mapped_column(ForeignKey("players.id"))
	fantasy_team_id = mapped_column(ForeignKey("fantasy_teams.id"))
	position = mapped_column(ForeignKey("positions.id"))

	player: Mapped[Player] = relationship(back_populates="fantasyplayer")
	fantasyteam: Mapped[FantasyTeam] = relationship(back_populates="fantasyplayers")

	def __repr__(self) -> str:
		return f"FantasyPlayer(id={self.id!r}, player_id={self.player_id!r}, fantasy_team_id={self.fantasy_team_id!r}, position={self.position!r})"

######################################
## Non-Mapped Classes
######################################

class Map:
	# non-mapped fields

	def __init__(self, game_id: int):
		self.game_id = game_id
		self.name = None
		self.team1 = None
		self.team2 = None

	def __str__(self) -> str:
		return f"{self.name}\tGame ID: {str(self.game_id)}\n\n{str(self.team1)}\n{str(self.team2)}"


class Match:
	# non-mapped fields

	def __init__(self, match_id: int):
		self.match_id = match_id
		self.maps = list()

	def __str__(self) -> str:
		rv = f"Match ID: {str(self.match_id)}\n"
		for map_ in self.maps:
			rv += "----------\n\n" + str(map_)
		return rv
	
	def get_map(self, game_id: int):
		for map_ in self.maps:
			if game_id == map_.game_id:
				return map_
		return None


######################################
## Helpers
######################################

def add_spaces(buff, length):
	"""
	Add spaces until the buffer is at least the provided length.
	"""
	rv = ""
	while (len(buff) + len(rv)) < length:
		rv += " "
	return rv
