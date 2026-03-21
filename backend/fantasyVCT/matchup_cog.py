import fantasyVCT.database as db
from fantasyVCT.scraper import Scraper
from fantasyVCT.matchup import (
	generate_schedule, compute_weekly_score, derive_record,
	get_season_chain, compute_round_offset,
)

from discord.ext import commands
from sqlalchemy import select


class MatchupCog(commands.Cog, name="Matchup"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Matchup cog: {error}")

	@commands.command()
	async def newseason(self, ctx, event_url: str):
		"""Create a new season from a vlr.gg event URL"""
		try:
			event_name, num_weeks = Scraper.parse_event_page(event_url)
		except Exception as e:
			return await ctx.send(f"Failed to parse event page: {e}")

		with self.bot.db_manager.create_session() as session:
			# Deactivate any existing active season
			existing = session.scalars(select(db.Season).where(db.Season.is_active == True)).all()
			for s in existing:
				s.is_active = False

			season = db.Season(name=event_name, event_url=event_url, num_weeks=num_weeks, is_active=True)
			session.add(season)
			session.flush()

			for i in range(1, num_weeks + 1):
				session.add(db.Week(season_id=season.id, week_number=i))

			session.commit()

		await ctx.send(f"Season created: **{event_name}** ({num_weeks} weeks). Use `!generateschedule` to build matchups.")

	@commands.command()
	async def generateschedule(self, ctx):
		"""Generate a round-robin matchup schedule for the active season"""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season. Use `!newseason <event_url>` first.")

			fteams = list(session.scalars(select(db.FantasyTeam)))
			if len(fteams) < 2:
				return await ctx.send("Need at least 2 registered fantasy teams to generate a schedule.")

			weeks = list(session.scalars(select(db.Week).where(db.Week.season_id == season.id)))
			week_map = {w.week_number: w.id for w in weeks}

			# Idempotency guard — abort if matchups already exist
			for week in weeks:
				if session.scalars(select(db.Matchup).where(db.Matchup.week_id == week.id)).first():
					return await ctx.send(
						"Matchups already exist for this season. "
						"Delete them manually before regenerating."
					)

			team_ids = [t.id for t in fteams]
			# Compute round offset for stage continuation
			round_offset = 0
			if season.previous_season_id is not None:
				chain = get_season_chain(season)
				total_prev_weeks = sum(s.num_weeks for s in chain[:-1])
				round_offset = compute_round_offset(total_prev_weeks, len(team_ids))
			schedule = generate_schedule(team_ids, season.num_weeks, round_offset)

			for week_idx, pairs in enumerate(schedule):
				week_number = week_idx + 1
				week_id = week_map.get(week_number)
				if not week_id:
					continue
				for home_id, away_id in pairs:
					session.add(db.Matchup(
						week_id=week_id,
						home_team_id=home_id,
						away_team_id=away_id,
						home_score=0.0,
						away_score=0.0
					))

			session.commit()

		team_count = len(fteams)
		await ctx.send(f"Schedule generated for {team_count} teams across {season.num_weeks} weeks.")

	@commands.command()
	async def closeweek(self, ctx, week_number: int):
		"""Finalize scores for a given week (locks home_score/away_score)"""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			week = session.scalars(
				select(db.Week).where(db.Week.season_id == season.id, db.Week.week_number == week_number)
			).first()
			if not week:
				return await ctx.send(f"Week {week_number} not found in active season.")

			matchups = list(session.scalars(select(db.Matchup).where(db.Matchup.week_id == week.id)))
			if not matchups:
				return await ctx.send(f"No matchups found for week {week_number}.")

			for matchup in matchups:
				matchup.home_score = compute_weekly_score(matchup.home_team_id, week.id, session)
				if matchup.away_team_id is not None:
					matchup.away_score = compute_weekly_score(matchup.away_team_id, week.id, session)
				else:
					# Ghost: mirror the home team's score (home always beats ghost)
					matchup.away_score = 0.0

			season.roster_locked = False
			session.commit()

		await ctx.send(f"Week {week_number} scores locked. Rosters are now unlocked.")

	@commands.command()
	async def lockroster(self, ctx):
		"""Lock all rosters for the active season. Use !closeweek to unlock."""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")
			season.roster_locked = True
			session.commit()
		await ctx.send("Rosters are now locked. No drops, adds, or position changes until !closeweek is run.")

	@commands.command()
	async def matchup(self, ctx, week: int = None):
		"""Show your matchup for the current (or specified) week"""
		author_id = ctx.message.author.id

		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			user = session.scalars(select(db.User).where(db.User.discord_id == author_id)).first()
			if not user or not user.fantasyteam:
				return await ctx.send("You don't have a registered fantasy team.")

			# Determine week
			if week is None:
				# Find the most recent week with uploaded results
				weeks = sorted(season.weeks, key=lambda w: w.week_number)
				target_week = weeks[0] if weeks else None
				for w in weeks:
					results_exist = session.scalars(
						select(db.Result).where(db.Result.week_id == w.id)
					).first()
					if results_exist:
						target_week = w
			else:
				target_week = session.scalars(
					select(db.Week).where(db.Week.season_id == season.id, db.Week.week_number == week)
				).first()

			if not target_week:
				return await ctx.send("No week data found.")

			my_team = user.fantasyteam
			matchup_row = session.scalars(
				select(db.Matchup).where(
					db.Matchup.week_id == target_week.id,
					(db.Matchup.home_team_id == my_team.id) | (db.Matchup.away_team_id == my_team.id)
				)
			).first()

			if not matchup_row:
				return await ctx.send(f"No matchup found for week {target_week.week_number}.")

			home_team = matchup_row.home_team
			away_team = matchup_row.away_team

			home_score = compute_weekly_score(home_team.id, target_week.id, session)
			away_score = compute_weekly_score(away_team.id, target_week.id, session) if away_team else 0.0

			buf = f"```\nWeek {target_week.week_number} Matchup — {season.name}\n"
			buf += f"{home_team.abbrev} / {home_team.name}: {home_score} pts\n"
			if away_team:
				buf += f"{away_team.abbrev} / {away_team.name}: {away_score} pts\n"
			else:
				buf += f"Ghost: {away_score} pts\n"
			buf += "```"
			await ctx.send(buf)

	@commands.command()
	async def schedule(self, ctx):
		"""Show the full season matchup schedule"""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			weeks = sorted(season.weeks, key=lambda w: w.week_number)
			if not weeks:
				return await ctx.send("No weeks found. Use `!generateschedule`.")

			buf = f"```\n{season.name} — Schedule\n\n"
			for week in weeks:
				matchups = list(session.scalars(select(db.Matchup).where(db.Matchup.week_id == week.id)))
				buf += f"Week {week.week_number}:\n"
				for m in matchups:
					away_label = m.away_team.abbrev if m.away_team else "Ghost"
					buf += f"  {m.home_team.abbrev} vs {away_label}\n"
				buf += "\n"
				if len(buf) > 1800:
					buf += "```"
					await ctx.send(buf)
					buf = "```\n"

			buf += "```"
			await ctx.send(buf)

	@commands.command()
	async def record(self, ctx):
		"""Show W/L/T standings across all stages of the active season"""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			# Walk chain to collect all season ids (all stages)
			chain = get_season_chain(season)
			all_season_ids = [s.id for s in chain]

			fteams = list(session.scalars(select(db.FantasyTeam)))
			records = []
			for fteam in fteams:
				matchups = list(session.scalars(
					select(db.Matchup).where(
						(db.Matchup.home_team_id == fteam.id) | (db.Matchup.away_team_id == fteam.id),
						db.Matchup.week_id.in_(
							select(db.Week.id).where(db.Week.season_id.in_(all_season_ids))
						)
					)
				))
				closed = [m for m in matchups if m.home_score > 0 or m.away_score > 0]
				w, l, t = derive_record(closed, fteam.id)

				# Total points across all stages
				all_weeks = [wk for s in chain for wk in s.weeks]
				total_pts = sum(compute_weekly_score(fteam.id, wk.id, session) for wk in all_weeks)
				records.append((fteam, w, l, t, round(total_pts, 1)))

			records.sort(key=lambda r: (-r[1], -r[4]))

			header = "Season Standings (all stages)" if len(chain) > 1 else f"Season Standings — {season.name}"
			buf = f"```\n{header}\n\n"
			buf += "  Team             W   L   T   Pts\n"
			for fteam, w, l, t, pts in records:
				name = f"{fteam.abbrev} / {fteam.name}"
				buf += f"  {name:<16} {w:<4}{l:<4}{t:<4}{pts}\n"
			buf += "```"
			await ctx.send(buf)


	@commands.command()
	async def continueseason(self, ctx, event_url: str):
		"""Start Stage 2 continuing from the active season (same teams, cumulative record)"""
		try:
			event_name, num_weeks = Scraper.parse_event_page(event_url)
		except Exception as e:
			return await ctx.send(f"Failed to parse event page: {e}")

		with self.bot.db_manager.create_session() as session:
			prev_season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not prev_season:
				return await ctx.send("No active season to continue from.")

			prev_id = prev_season.id
			prev_season.is_active = False

			new_season = db.Season(
				name=event_name,
				event_url=event_url,
				num_weeks=num_weeks,
				is_active=True,
				previous_season_id=prev_id,
			)
			session.add(new_season)
			session.flush()

			for i in range(1, num_weeks + 1):
				session.add(db.Week(season_id=new_season.id, week_number=i))

			# Track the primary event URL in season_events as well
			session.add(db.SeasonEvent(season_id=new_season.id, event_url=event_url))
			session.commit()

		await ctx.send(
			f"Season continued: **{event_name}** ({num_weeks} weeks). "
			f"Run `!generateschedule` to build matchups (round offset applied automatically)."
		)

	@commands.command()
	async def addevent(self, ctx, event_url: str):
		"""Add a regional event URL to the active season"""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			# Try to get the event name for confirmation display
			try:
				event_name, _ = Scraper.parse_event_page(event_url)
			except Exception:
				event_name = event_url

			session.add(db.SeasonEvent(season_id=season.id, event_url=event_url))
			session.commit()

		await ctx.send(f"Added event **{event_name}** to active season.")


async def setup(bot):
	await bot.add_cog(MatchupCog(bot))
