from fantasyVCT.scoring import PointCalculator
import fantasyVCT.database as db

from discord.ext import commands
from sqlalchemy import select, or_

from fantasyVCT.utils import add_spaces


class ConfigCog(commands.Cog, name="Configuration"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Config cog: {error}")

	@commands.command()
	async def register(self, ctx, team_abbrev: str, *team_name_list: str):
		"""Register a team"""
		team_name = " ".join(team_name_list)
		author_id = ctx.message.author.id

		with self.bot.db_manager.create_session() as session:
			stmt = select(db.User).filter_by(discord_id=author_id)
			author = session.execute(stmt).scalar_one_or_none()
			if author and author.fantasyteam:
				return await ctx.send("You have already registered a team.")

			fteams = session.scalars(select(db.FantasyTeam).where(
				or_(
					db.FantasyTeam.name == team_name,
					db.FantasyTeam.abbrev == team_abbrev
				)
			))
			for fteam in fteams:
				if fteam.name == team_name:
					return await ctx.send(f"{team_name} is taken, please choose another name.")
				elif fteam.abbrev == team_abbrev:
					return await ctx.send(f"{team_abbrev} is taken, please choose another abbreviation.")

			if not author:
				author = db.User(discord_id=author_id)

			new_fteam = db.FantasyTeam(name=team_name, abbrev=team_abbrev)
			author.fantasyteam = new_fteam

			session.add_all([author, new_fteam])
			session.flush()
			session.commit()

		await ctx.send(f"{team_abbrev} {team_name} has been registered for {ctx.message.author.mention}")

	@commands.command()
	async def skipdraft(self, ctx):
		"""Skip past the draft step."""
		self.bot.draft_state.skip_draft()

	@commands.command()
	async def trackevent(self, ctx, event_name: str):
		"""Start tracking matches from an event"""
		with self.bot.db_manager.create_session() as session:
			event = session.execute(select(db.Event).filter_by(name=event_name)).scalar_one_or_none()
			if event:
				return await ctx.send(f"{event_name} is already being tracked.")

			event = db.Event(name=event_name)
			session.add(event)
			session.flush()
			session.commit()

		await ctx.send(f"Started tracking {event_name}.")

	@commands.command()
	async def untrackevent(self, ctx, event_name: str):
		"""Stop tracking new matches from an event"""
		with self.bot.db_manager.create_session() as session:
			event = session.execute(select(db.Event).filter_by(name=event_name)).scalar_one_or_none()
			if not event:
				return await ctx.send("{event_name} is not currently being tracked.")

			session.delete(event)
			session.flush()
			session.commit()

		await ctx.send(f"Stopped tracking {event_name}.")

	@commands.command()
	async def startdraft(self, ctx):
		"""Begin the draft"""
		if self.bot.draft_state.is_draft_complete():
			return await ctx.send("Draft is already complete.")
		elif self.bot.draft_state.is_draft_started():
			return await ctx.send("Draft has already begun.")

		with self.bot.db_manager.create_session() as session:
			registered_users = session.scalars(select(db.User.discord_id))
			users_list = list(registered_users)

			next_drafter = self.bot.draft_state.start_draft(users_list)
			await ctx.send(f"It is <@!{next_drafter}>'s turn!")

	@commands.command()
	async def newteam(self, ctx, url: str):
		"""Upload a team and players to the database using a vlr.gg team url"""
		if self.bot.draft_state.is_draft_started():
			return await ctx.send("Cannot add additional teams/players once draft has started.")
		team_name, team_abbrev, player_names = self.bot.scraper.parse_team(url)

		with self.bot.db_manager.create_session() as session:
			team = session.execute(select(db.Team).filter_by(name=team_name)).scalar_one_or_none()
			if not team:
				team = db.Team(name=team_name, abbrev=team_abbrev)
				session.add(team)

			for player_name in player_names:
				player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
				if not player:
					player = db.Player(name=player_name)
					session.add(player)
				player.team = team
			session.flush()
			session.commit()
			return await ctx.invoke(self.bot.get_command('info'), team_name)

	@commands.command()
	async def rules(self, ctx):
		"""Display rules"""
		buf = "```\n"
		buf += "How to play:\n"
		buf += "- Draft a team of valorant players, and compete to see who whose players have the best performance over the course of the event\n"
		buf += "- Players will receive points based on their performance in the games\n"
		buf += "- During the draft phase, participants will take turns picking players for their teams\n"
		buf == "- Until the draft phase is over, you will not be able to add or drop players outside of your turn\n"
		buf += "- After the draft phase, you can add, drop and move players as much as you'd like\n"
		buf += "- Each team can only have ONE player from a given team. i.e. you can only have one member of 100 Thieves on your active roster\n"
		buf += "- Each team has 6 active slots and " + str(self.bot.sub_slots) + " sub slot(s)\n"
		buf += "- The Captain role is a special role that does not follow the 'one player from each team' restriction. You can have a player from ANY team as your flex, even if you already have a player from that team\n"
		buf += "- Only players in active slots count towards your team's total points\n"
		buf += "- At the end of the event, the fantasy team with the most total points wins\n"
		buf += "\n"
		buf += "Draft phase:\n"
		buf += "- There will be " + str(self.bot.num_rounds) + " rounds\n"
		buf += "- Snake draft (1234554321123...)\n"
		buf += "- The draft is asynchronous, and you will be pinged when it is your turn to draft\n"
		buf += "```"
		return await ctx.send(buf)

	@commands.command()
	async def scoring(self, ctx):
		"""Display scoring information"""
		buf = "```\n"
		buf += PointCalculator.get_scoring_info()
		buf += "```"
		return await ctx.send(buf)


async def setup(bot):
	await bot.add_cog(ConfigCog(bot))
