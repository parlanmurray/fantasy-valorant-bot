import os
import argparse
import asyncio

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import setup
from fantasyVCT.vlr_api import fetch_setup

from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')
DB_TYPE = os.getenv('DATABASE_TYPE')
DB_DEV = os.getenv('DATABASE_DEV')
DB_PROD = os.getenv('DATABASE_PROD')

if not DB_USER:
	print("No database user specified. Check .env file.")
	exit(1)
elif not DB_PASSWORD:
	print("No database password specified. Check .env file.")
	exit(1)
elif not TOKEN:
	print("No discord token specified. Check .env file.")
	exit(1)
elif not DB_DEV:
	print("No development database specified. Check .env file.")
	exit(1)
elif not DB_PROD:
	print("No production database specified. Check .env file.")
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
