from fantasyVCT.valorant import Player

from typing import List

from sqlalchemy import create_engine
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
	pass


def query_precheck(func):
	def wrapper(*args):
		if not args[0].is_open():
			print("Database connection been closed due to timeout. Reopening...")
		args[0].open()
		return func(*args)
	return wrapper


class DatabaseManager:
	def __init__(self, type, user, password, database, host = "127.0.0.1"):
		self.user = user
		self.password = password
		self.database = database
		self.host = host
		self.type = type
		self.uri_string = f"{self.type}://{self.user}:{self.password}@localhost/{self.database}"
		# "mysql://<user>:<password>@localhost/FantasyValProd"
		self._engine = create_engine(self.uri_string)


	# def open(self):
	# 	if self.is_open():
	# 		return
	# 	self._conn = mysql.connector.connect(user=self.user, password=self.password,
	# 										 host=self.host, database=self.database)

	# def close(self):
	# 	if self._conn:
	# 		self._conn.close()
	# 		self._conn = None

	def connect(self):
		"""
		Caller is repsonsible for Connection object.
		"""
		return self._engine.connect()

	def create_session(self):
		"""
		Caller is responsible for Session object.
		"""
		return Session(self._engine)


######################################
## Mapped Classes
######################################

class Team(Base):
	__tablename__ = "teams"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False)
	abbrev: Mapped[str] = mapped_column(String(10), nullable=False)
	region: Mapped[str] = mapped_column(String[10])

	players: Mapped[List["Player"]] = relationship(back_populates="team")

	def __repr__(self) -> str:
		return f"Team(id={self.id!r}, name={self.name!r}, abbrev={self.abbrev!r}, region={self.region!r})"


class Player(Base):
	__tablename__ = "players"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False)
	team_id = mapped_column(ForeignKey("teams.id"))
	
	team: Mapped[Team] = relationship(back_populates="players")
	results: Mapped[List["Result"]] = relationship(back_populates="player")
	fantasyplayer: Mapped["FantasyPlayer"] = relationship(back_populates="player")

	def __repr__(self) -> str:
		return f"Player(id={self.id!r}, name={self.name!r}, team_id={self.team_id!r})"


class Event(Base):
	__tablename__ = "events"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(80), nullable=False)


class Result(Base):
	__tablename__ = "results"

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

	player: Mapped[Player] = relationship(back_populates="results")

	def __repr__(self) -> str:
		return (
			f"Result(id={self.id!r}, map={self.map!r}, game_id={self.game_id!r}, "
			f"match_id={self.match_id!r}, event_id={self.event_id!r}, player_id={self.player_id!r})"
			# TODO more fields?
		)

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
