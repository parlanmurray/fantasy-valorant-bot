import os

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import Test, StatsCog, FantasyCog

from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

USE_DEV = True


def retrieve_results_from_api(bot):
	json = get_results()
	bot.process_results(json)


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

	# start scheduler
	scheduler = AsyncIOScheduler()
	scheduler.add_job(retrieve_results_from_api, 'interval', hours=1, id='id_retrieve_results_from_api', args=(bot))
	scheduler.start()

	# configure and start bot
	bot.add_cog(StatsCog(bot))
	bot.add_cog(FantasyCog(bot))
	bot.run(TOKEN)


if __name__ == "__main__":
	main()
