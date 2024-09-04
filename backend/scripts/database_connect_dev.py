import os

from fantasyVCT.database import DatabaseManager
import fantasyVCT.database as db

from sqlalchemy import select

DB_PASSWORD_FILE = os.getenv('DATABASE_PASSWORD_FILE')
DB_USER = os.getenv('DATABASE_USER')
DB_TYPE = os.getenv('DATABASE_TYPE')
DB_DEV = os.getenv('DATABASE_DEV')
DB_PASSWORD = None

if not DB_PASSWORD_FILE:
	print("No database password file specified.")
	exit(1)

with open(DB_PASSWORD_FILE, 'r') as f:
	DB_PASSWORD_FILE = f.read()

if not DB_USER:
	print("No database user specified.")
	exit(1)
elif not DB_PASSWORD:
	print("No database password specified. Did you create db/password.txt?")
	exit(1)
elif not DB_DEV:
	print("No development database specified.")
	exit(1)

db_manager = DatabaseManager(DB_TYPE, DB_USER, DB_PASSWORD, DB_DEV)

session = db_manager.create_session()
