"""DatabaseManager unit tests using SQLite in-memory — no live DB required."""
import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session as SASession

from fantasyVCT.database import Base, DatabaseManager, Team, Player
from sqlalchemy import select


@pytest.fixture
def engine():
	eng = create_engine("sqlite:///:memory:")

	@event.listens_for(eng, "connect")
	def set_fk(dbapi_conn, _):
		cursor = dbapi_conn.cursor()
		cursor.execute("PRAGMA foreign_keys = ON")
		cursor.close()

	Base.metadata.create_all(eng)
	yield eng
	eng.dispose()


@pytest.fixture
def db_manager(engine):
	return DatabaseManager.from_engine(engine)


def test_connect(db_manager, engine):
	"""Engine connects and all ORM tables are present."""
	with db_manager.connect():
		table_names = inspect(engine).get_table_names()
	assert "players" in table_names
	assert "teams" in table_names
	assert "results" in table_names


def test_create_session_add_and_query(db_manager):
	"""Session can add a Player and query it back."""
	with db_manager.create_session() as session:
		team = Team(name="TestTeam", abbrev="TST", region="na")
		session.add(team)
		session.flush()

		player = Player(name="TestPlayer", team_id=team.id)
		session.add(player)
		session.flush()

		found = session.scalars(select(Player).where(Player.name == "TestPlayer")).one()
		assert found.name == "TestPlayer"
		assert found.team_id == team.id

		session.rollback()
