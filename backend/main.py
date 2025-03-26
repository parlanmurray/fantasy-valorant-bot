import os
import argparse
import asyncio

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import setup
from fantasyVCT.vlr_api import fetch_setup


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

# parse args
# these arguments get automatically added to the bot as variables
parser = argparse.ArgumentParser()
parser.add_argument('--skip-draft', action='store_true', help='skip the draft step')
parser.add_argument('-r', '--rounds', dest='num_rounds', action='store', default=7, type=int, help="number of draft rounds")
parser.add_argument('-s', '--subs', dest='sub_slots', action='store', default=2, type=int, help="number of sub slots allowed per team")
parser.add_argument('--prod', action='store_true', help='use production database instead of development database')

bot = FantasyValBot("!")

parser.parse_args(namespace=bot)

bot.configure_db(DB_USER, DB_PASSWORD, DB_DEV, DB_PROD, db_type=DB_TYPE)

async def main():
	async with bot:
		# configure and start bot
		await setup(bot)
		await fetch_setup(bot)
		await bot.start(TOKEN)


if __name__ == "__main__":
	asyncio.run(main())
