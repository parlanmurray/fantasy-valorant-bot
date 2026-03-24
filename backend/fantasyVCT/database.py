from enum import Enum
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
	pass


class DatabaseManager:
	def __init__(self, type, user, password, database, host = "127.0.0.1"):
		self.user = user
		self.password = password
		self.database = database
		self.host = host
		self.type = type
		self.uri_string = f"{self.type}://{self.user}:{self.password}@{self.host}/{self.database}?charset=utf8mb4"
		# "mysql://<user>:<password>@localhost/FantasyValProd"
		self._engine = create_engine(self.uri_string, pool_pre_ping=True)

	@classmethod
	def from_engine(cls, engine):
		"""Create a DatabaseManager from a pre-built engine (e.g. SQLite for tests)."""
		obj = cls.__new__(cls)
		obj._engine = engine
		return obj

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
	region: Mapped[str] = mapped_column(String(10))

	# relationship fields
	players: Mapped[List["Player"]] = relationship(back_populates="team")

	# other fields
	won: bool = False
	score: int = 0
	map_pick: bool = False

	def __repr__(self) -> str:
		return f"Team(id={self.id!r}, name={self.name!r}, abbrev={self.abbrev!r}, region={self.region!r})"

	def __str__(self) -> str:
		format_str = self.abbrev + " / " + self.name
		format_str = f"{format_str:<30}{self.score}"
		if self.won:
			format_str += " -- Winner"
		if self.map_pick:
			format_str += " -- Map Pick"
		line = "Player"
		line = f"{line:<20}Agent"
		line = f"{line:<40}ACS"
		line = f"{line:<50}K/D/A"
		line = f"{line:<80}2k"
		line = f"{line:<90}3k"
		line = f"{line:<100}4k"
		line = f"{line:<110}5k"
		line = f"{line:<120}1v2"
		line = f"{line:<130}1v3"
		line = f"{line:<140}1v4"
		line = f"{line:<150}1v5"
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
			line = f"{line:<20}{result}"
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
	player_fk: Mapped[Optional[int]]
	rounds_played: Mapped[Optional[int]]
	rounds_won: Mapped[Optional[int]]
	team_won: Mapped[Optional[bool]]
	agent: Mapped[str] = mapped_column(String(20))
	week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), nullable=True, default=None)

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
		line = f"{line:<20}{self.player_acs}"
		line = f"{line:<30}{self.player_kills}/{self.player_deaths}/{self.player_assists}"
		line = f"{line:<60}{self.player_2k}"
		line = f"{line:<70}{self.player_3k}"
		line = f"{line:<80}{self.player_4k}"
		line = f"{line:<90}{self.player_5k}"
		line = f"{line:<100}{self.player_clutch_v2}"
		line = f"{line:<110}{self.player_clutch_v3}"
		line = f"{line:<120}{self.player_clutch_v4}"
		line = f"{line:<130}{self.player_clutch_v5}"
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

class Season(Base):
	__tablename__ = "seasons"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	event_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	num_weeks: Mapped[int] = mapped_column(nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean, default=False)
	roster_locked: Mapped[bool] = mapped_column(Boolean, default=False)
	previous_season_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seasons.id"), nullable=True)

	weeks: Mapped[List["Week"]] = relationship(back_populates="season")
	previous_season: Mapped[Optional["Season"]] = relationship(
		"Season", foreign_keys=[previous_season_id], remote_side="Season.id"
	)
	season_event_urls: Mapped[List["SeasonEvent"]] = relationship(back_populates="season")

	def __repr__(self) -> str:
		return f"Season(id={self.id!r}, name={self.name!r}, num_weeks={self.num_weeks!r}, is_active={self.is_active!r})"


class SeasonEvent(Base):
	__tablename__ = "season_events"

	id: Mapped[int] = mapped_column(primary_key=True)
	season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
	event_url: Mapped[str] = mapped_column(String(255), nullable=False)

	season: Mapped[Season] = relationship(back_populates="season_event_urls")

	def __repr__(self) -> str:
		return f"SeasonEvent(id={self.id!r}, season_id={self.season_id!r}, event_url={self.event_url!r})"


class Week(Base):
	__tablename__ = "weeks"

	id: Mapped[int] = mapped_column(primary_key=True)
	season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
	week_number: Mapped[int] = mapped_column(nullable=False)

	season: Mapped[Season] = relationship(back_populates="weeks")
	matchups: Mapped[List["Matchup"]] = relationship(back_populates="week")

	def __repr__(self) -> str:
		return f"Week(id={self.id!r}, season_id={self.season_id!r}, week_number={self.week_number!r})"


class Matchup(Base):
	__tablename__ = "matchups"

	id: Mapped[int] = mapped_column(primary_key=True)
	week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), nullable=False)
	home_team_id: Mapped[int] = mapped_column(ForeignKey("fantasy_teams.id"), nullable=False)
	away_team_id: Mapped[int] = mapped_column(ForeignKey("fantasy_teams.id"), nullable=True)
	ghost_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fantasy_teams.id"), nullable=True)
	home_score: Mapped[float] = mapped_column(default=0.0)
	away_score: Mapped[float] = mapped_column(default=0.0)

	week: Mapped[Week] = relationship(back_populates="matchups")
	home_team: Mapped[FantasyTeam] = relationship(foreign_keys=[home_team_id])
	away_team: Mapped[FantasyTeam] = relationship(foreign_keys=[away_team_id])
	ghost_team: Mapped[Optional[FantasyTeam]] = relationship(foreign_keys=[ghost_team_id])

	def __repr__(self) -> str:
		return (
			f"Matchup(id={self.id!r}, week_id={self.week_id!r}, "
			f"home_team_id={self.home_team_id!r}, away_team_id={self.away_team_id!r})"
		)


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

