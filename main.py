import os

from dotenv import load_dotenv

from fantasyVCT.bot import FantasyValBot
from fantasyVCT.interactions import Test

def main():
	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')
	print(TOKEN)

	bot = FantasyValBot("!")
	bot.add_cog(Test(bot))
	bot.run(TOKEN)

if __name__ == "__main__":
	main()
