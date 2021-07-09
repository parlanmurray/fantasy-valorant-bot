import os

from dotenv import load_dotenv

from discordbot.bot import FantasyValBot
from discordbot.interactions import Test

def main():
	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')
	print(TOKEN)

	bot = FantasyValBot("!")
	bot.add_cog(Test(bot))
	bot.run(TOKEN)

if __name__ == "__main__":
	main()
