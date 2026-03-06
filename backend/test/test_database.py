import os

import pytest
from fantasyVCT.database import DatabaseManager, Player
from sqlalchemy import select

# Requires a live DB + env vars — skips cleanly when not available.

TOKEN_FILE = os.getenv('DISCORD_TOKEN_FILE')
DB_PASSWORD_FILE = os.getenv('DATABASE_PASSWORD_FILE')
DB_USER = os.getenv('DATABASE_USER')
DB_TYPE = os.getenv('DATABASE_TYPE')
DB_DEV = os.getenv('DATABASE_DEV')
DB_PROD = os.getenv('DATABASE_PROD')

_missing = [
    v for v, name in [
        (TOKEN_FILE, 'DISCORD_TOKEN_FILE'),
        (DB_PASSWORD_FILE, 'DATABASE_PASSWORD_FILE'),
        (DB_USER, 'DATABASE_USER'),
        (DB_TYPE, 'DATABASE_TYPE'),
        (DB_DEV, 'DATABASE_DEV'),
        (DB_PROD, 'DATABASE_PROD'),
    ] if not v
]

pytestmark = pytest.mark.skipif(
    bool(_missing),
    reason=f"DB env vars not set: {_missing}"
)

DB_PASSWORD = None
TOKEN = None

if not _missing:
    with open(DB_PASSWORD_FILE, 'r') as f:
        DB_PASSWORD = f.read()
    with open(TOKEN_FILE, 'r') as f:
        TOKEN = f.read()
    db_manager = DatabaseManager(DB_TYPE, DB_USER, DB_PASSWORD, DB_DEV)
else:
    db_manager = None


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
