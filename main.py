import os

from dotenv import load_dotenv

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import Test, StatsCog, FantasyCog

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
	bot.add_cog(Test(bot))
	bot.add_cog(StatsCog(bot))
	bot.add_cog(FantasyCog(bot))
	bot.run(TOKEN)

if __name__ == "__main__":
	main()
