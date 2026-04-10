from fantasyVCT.scoring import PointCalculator
import fantasyVCT.database as db

from discord.ext import commands
from sqlalchemy import select, or_

from fantasyVCT.utils import POSITIONS


class ConfigCog(commands.Cog, name="Configuration"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Config cog: {error}")

	@commands.command()
	async def register(self, ctx, team_abbrev: str, *team_name_list: str):
		"""Register a fantasy team.

		Parameters:
		-----------
		team_abbrev: Short abbreviation for your team (e.g. TSM).
		team_name: Full name of your team (e.g. Team SoloMid).
		"""
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
		"""Skip the draft phase and go straight to free agency."""
		self.bot.draft_state.skip_draft()

	@commands.command()
	async def trackevent(self, ctx, event_name: str):
		"""Start tracking matches from a VCT event.

		Parameters:
		-----------
		event_name: Exact event name as it appears on vlr.gg (e.g. "VCT 2025 Americas Stage 1").
		"""
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
		"""Stop tracking new matches from a VCT event.

		Parameters:
		-----------
		event_name: Exact event name as it appears on vlr.gg (e.g. "VCT 2025 Americas Stage 1").
		"""
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
		"""Begin the snake draft. All teams must be registered first."""
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
	async def scrapeevent(self, ctx):
		"""Scrape all teams and players from the active season's event URLs."""
		if self.bot.draft_state.is_draft_started():
			return await ctx.send("Cannot add teams/players once draft has started.")

		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")
			event_urls = [se.event_url for se in season.season_event_urls]

		if not event_urls:
			return await ctx.send("No event URLs attached to active season. Use `!seteventurl` or `!addevent` first.")

		await ctx.send(f"Scraping {len(event_urls)} event(s)...")

		all_team_urls = []
		seen = set()
		for event_url in event_urls:
			try:
				team_urls = self.bot.scraper.parse_event_teams(event_url)
				for url in team_urls:
					if url not in seen:
						seen.add(url)
						all_team_urls.append(url)
			except Exception as e:
				await ctx.send(f"Failed to scrape {event_url}: {e}")

		if not all_team_urls:
			return await ctx.send("No teams found on event pages.")

		added = 0
		updated = 0
		failed = 0
		for team_url in all_team_urls:
			try:
				team_name, team_abbrev, player_names = self.bot.scraper.parse_team(team_url)
				with self.bot.db_manager.create_session() as session:
					team = session.execute(select(db.Team).filter_by(name=team_name)).scalar_one_or_none()
					if not team:
						team = db.Team(name=team_name, abbrev=team_abbrev)
						session.add(team)
						added += 1
					else:
						updated += 1
					for player_name in player_names:
						player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
						if not player:
							player = db.Player(name=player_name)
							session.add(player)
						player.team = team
					session.commit()
			except Exception as e:
				await ctx.send(f"Failed to scrape team {team_url}: {e}")
				failed += 1

		await ctx.send(f"Done. {added} teams added, {updated} updated, {failed} failed. {len(all_team_urls) - failed} teams total.")

	@commands.command()
	async def newteam(self, ctx, url: str):
		"""Add a pro team and its players from vlr.gg.

		Parameters:
		-----------
		url: vlr.gg team URL (e.g. https://www.vlr.gg/team/2404/100-thieves).
		"""
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
		"""Display league rules and how scoring works."""
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
		"""Display the stat weights used to calculate fantasy points."""
		buf = "```\n"
		buf += PointCalculator.get_scoring_info()
		buf += "```"
		return await ctx.send(buf)

	@commands.command()
	async def roles(self, ctx):
		"""Display each role's mechanic and bonus weights."""
		buf = "```\n"
		buf += "Role-Based Scoring\n\n"
		col_r, col_m = 18, 60
		header = f"    Role"
		header = f"{header:<{col_r}}Mechanic"
		header = f"{header:<{col_m}}Weights"
		buf += header + "\n"
		buf += "    " + "-" * 76 + "\n"
		rows = [
			("IGL",        "Bonus when their pro team wins the map",  "+8.5 per win"),
			("Duelist",    "Bonus for first kills",                   "+2.0/FK  (3.0 total)"),
			("Initiator",  "Bonus for assists",                       "+1.0/assist  (1.5 total)"),
			("Controller", "Bonus for assists and rounds survived",   "+0.65/assist  +0.35/survived"),
			("Sentinel",   "Reduced death penalty",                   "-0.60/death  (saves 0.40)"),
			("Flex",       "No bonus -- bypasses team restriction",   "--"),
		]
		for role, mechanic, weights in rows:
			line = f"    {role}"
			line = f"{line:<{col_r}}{mechanic}"
			line = f"{line:<{col_m}}{weights}"
			buf += line + "\n"
		buf += "\n"
		buf += "The goal of role-based scoring is to make managing your fantasy team feel more\n"
		buf += "like managing a real Valorant team. Choosing which role a player will fill each\n"
		buf += "week will matter -- choosing well could be the difference between a win and a loss.\n"
		buf += "```"
		return await ctx.send(buf)


async def setup(bot):
	await bot.add_cog(ConfigCog(bot))
