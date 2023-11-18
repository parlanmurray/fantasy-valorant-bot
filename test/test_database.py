

from fantasyVCT.database import DatabaseManager, Player

from dotenv import dotenv_values
from sqlalchemy import select

config = dotenv_values("../.env")

db_manager = DatabaseManager(
    config["DATABASE_TYPE"],
    config["DATABASE_USER"],
    config["DATABASE_PASSWORD"],
    config["DATABASE_NAME"]
)


def test_connect():
    with db_manager.connect():
        assert True


def test_update():
    with db_manager.create_session() as session:
        sandy = Player(name="sandy", team_id=None)
        session.add(sandy)
        stmt = select(Player).where(Player.name.in_("sandy"))
        assert session.scalars(stmt)
        for player in session.scalars(stmt):
            print(player)
        session.rollback()
