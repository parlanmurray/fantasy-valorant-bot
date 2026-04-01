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
		buf = "How to play:\n"
		buf += "- Draft a team of VCT pro players and compete head-to-head each week\n"
		buf += "- Players score points based on their stats each map (see !scoring)\n"
		buf += "- Each week, the fantasy team with the higher score wins the matchup\n"
		buf += "- The team with the best record at the end of the season wins\n"
		buf += "\n"
		buf += "Roster management:\n"
		buf += f"- Each team has 6 active slots (IGL, Duelist, Initiator, Controller, Sentinel, Flex) and {self.bot.sub_slots} sub slot(s)\n"
		buf += "- Only active slots score points — subs do not\n"
		buf += "- IGL through Sentinel must each be from a different pro team; Flex is exempt\n"
		buf += "- Each week: assign roles with !set or !setall, then lock your roster with !lockroster\n"
		buf += "- Rosters unlock after !closeweek\n"
		buf += "\n"
		buf += "Role bonuses:\n"
		buf += "- Each active slot has a stat bonus on top of base score (see !roles)\n"
		buf += "- Placing the right player in the right role can swing a week\n"
		buf += "\n"
		buf += "Draft:\n"
		buf += f"- {self.bot.num_rounds} rounds, snake format (1-2-3...3-2-1...)\n"
		buf += "- Asynchronous — you will be pinged when it is your turn\n"
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
		buf += f"  {'Role':<12}Weights\n"
		buf += "  " + "─" * 36 + "\n"
		rows = [
			("IGL",        "+8.5/win"),
			("Duelist",    "+2.0/FK  (3.0 total w/ base)"),
			("Initiator",  "+1.0/assist  (1.5 total)"),
			("Controller", "+0.65/assist  +0.35/survived round"),
			("Sentinel",   "-0.60/death  (saves 0.40/death)"),
			("Flex",       "no bonus -- bypasses team restriction"),
		]
		for role, weights in rows:
			buf += f"  {role:<12}{weights}\n"
		buf += "\n"
		buf += "The goal of role-based scoring is to make managing\n"
		buf += "your fantasy team feel more like managing a real\n"
		buf += "Valorant team. Choosing which role a player fills\n"
		buf += "each week will matter -- it could be the difference\n"
		buf += "between a win and a loss.\n"
		buf += "```"
		return await ctx.send(buf)


async def setup(bot):
	await bot.add_cog(ConfigCog(bot))
