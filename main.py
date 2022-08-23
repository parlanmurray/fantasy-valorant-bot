import os
import argparse

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import StatsCog, FantasyCog, ConfigCog
from fantasyVCT.vlr_api import FetchCog

from dotenv import load_dotenv

USE_DEV = True


def main():
	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')
	DB_USER = os.getenv('DATABASE_USER')
	DB_PASSWORD = os.getenv('DATABASE_PASSWORD')

	if USE_DEV:
		DB_NAME = os.getenv('DATABASE_DEV')
	else:
		DB_NAME = os.getenv('DATABASE_PROD')

	bot = FantasyValBot("!", DB_USER, DB_PASSWORD, DB_NAME)

	# parse args
	# these arguments get automatically added to the bot as variables
	parser = argparse.ArgumentParser()
	parser.add_argument('--skip-draft', action='store_true', help='skip the draft step')
	parser.add_argument('-r', '--rounds', dest='num_rounds', action='store', default=7, type=int, help="number of draft rounds")
	parser.add_argument('-s', '--subs', dest='sub_slots', action='store', default=2, type=int, help="number of sub slots allowed per team")
	parser.parse_args(namespace=bot)

	# configure and start bot
	bot.add_cog(StatsCog(bot))
	bot.add_cog(FantasyCog(bot))
	bot.add_cog(FetchCog(bot))
	bot.add_cog(ConfigCog(bot))
	bot.run(TOKEN)


if __name__ == "__main__":
	main()
