import os
import argparse
import asyncio

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import setup
from fantasyVCT.vlr_api import fetch_setup

from dotenv import load_dotenv

USE_DEV = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')
DB_TYPE = os.getenv('DATABASE_TYPE')

if USE_DEV:
	DB_NAME = os.getenv('DATABASE_DEV')
else:
	DB_NAME = os.getenv('DATABASE_PROD')

if not DB_USER:
	print("No database user specified. Check .env file.")
	exit(1)
elif not DB_PASSWORD:
	print("No database password specified. Check .env file.")
	exit(1)
elif not DB_NAME:
	print("No database name specified. Check .env file.")
	exit(1)
elif not TOKEN:
	print("No discord token specified. Check .env file.")
	exit(1)

bot = FantasyValBot("!", DB_USER, DB_PASSWORD, DB_NAME, db_type=DB_TYPE)

async def main():
	# parse args
	# these arguments get automatically added to the bot as variables
	parser = argparse.ArgumentParser()
	parser.add_argument('--skip-draft', action='store_true', help='skip the draft step')
	parser.add_argument('-r', '--rounds', dest='num_rounds', action='store', default=7, type=int, help="number of draft rounds")
	parser.add_argument('-s', '--subs', dest='sub_slots', action='store', default=2, type=int, help="number of sub slots allowed per team")
	parser.parse_args(namespace=bot)

	async with bot:
		# configure and start bot
		await setup(bot)
		# await fetch_setup(bot)
		await bot.start(TOKEN)


if __name__ == "__main__":
	asyncio.run(main())
