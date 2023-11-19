
from fantasyVCT.database import DatabaseManager
import fantasyVCT.database as db

from dotenv import dotenv_values
from sqlalchemy import select

config = dotenv_values(".env")

db_manager = DatabaseManager(
    config["DATABASE_TYPE"],
    config["DATABASE_USER"],
    config["DATABASE_PASSWORD"],
    config["DATABASE_DEV"]
)
