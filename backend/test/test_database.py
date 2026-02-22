import os

from fantasyVCT.database import DatabaseManager, Player

from sqlalchemy import select

# unit testing for database
# requires database on host machine
# run with pytest

TOKEN_FILE = os.getenv('DISCORD_TOKEN_FILE')
DB_PASSWORD_FILE = os.getenv('DATABASE_PASSWORD_FILE')
DB_USER = os.getenv('DATABASE_USER')
DB_TYPE = os.getenv('DATABASE_TYPE')
DB_DEV = os.getenv('DATABASE_DEV')
DB_PROD = os.getenv('DATABASE_PROD')
DB_PASSWORD = None
TOKEN = None

if not TOKEN_FILE:
	print("No discord token file specified.")
	exit(1)
elif not DB_PASSWORD_FILE:
	print("No database password file specified.")
	exit(1)

with open(DB_PASSWORD_FILE, 'r') as f:
	DB_PASSWORD = f.read()

with open(TOKEN_FILE, 'r') as f:
	TOKEN = f.read()

if not DB_USER:
	print("No database user specified.")
	exit(1)
elif not DB_PASSWORD:
	print("No database password specified. Did you create db/password.txt?")
	exit(1)
elif not TOKEN:
	print("No discord token specified. Did you create backend/discord_token.txt?")
	exit(1)
elif not DB_DEV:
	print("No development database specified.")
	exit(1)
elif not DB_PROD:
	print("No production database specified.")
	exit(1)

db_manager = DatabaseManager(DB_TYPE, DB_USER, DB_PASSWORD, DB_DEV)


def test_connect():
    with db_manager.connect():
        assert True


def test_update():
    with db_manager.create_session() as session:
        sandy = Player(name="sandy", team_id=None)
        session.add(sandy)
        stmt = select(Player).where(Player.name.in_(["sandy"]))
        assert session.scalars(stmt)
        session.rollback()
