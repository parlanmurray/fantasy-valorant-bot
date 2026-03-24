import fantasyVCT.database as db
from fantasyVCT.scraper import Scraper
from fantasyVCT.matchup import (
	generate_schedule, compute_weekly_score, derive_record,
	get_season_chain, compute_round_offset,
	week_role_leaders, week_top_base_scorers,
)

from discord.ext import commands
from sqlalchemy import select


def _fmt_week_summary(week_number: int, matchups: list, week_id: int, fteams: list, session) -> list[str]:
	"""Build week summary message strings (sections 1–3). Returns list of Discord messages."""
	SEP = "═" * 42

	# ── Section 1: Matchup Results ─────────────────────────────
	lines = [f"```\n{SEP}", f" WEEK {week_number} RESULTS", SEP]
	for m in matchups:
		home = m.home_team.abbrev
		hs   = m.home_score
		aws  = m.away_score
		if m.away_team_id is not None:
			away = m.away_team.abbrev
			verb = "def" if hs >= aws else "lost to"
			lines.append(f" {home:<5} {hs:>6.1f}  {verb}  {away:<5} {aws:>6.1f}")
		else:
			mirror = m.ghost_team.abbrev if m.ghost_team else "?"
			verb   = "def" if hs >= aws else "lost to"
			lines.append(f" {home:<5} {hs:>6.1f}  {verb}  GHOST  {aws:>6.1f}  (via {mirror})")
	lines.append(f"{SEP}```")
	msg1 = "\n".join(lines)

	# ── Section 2: Top Performers by Role ──────────────────────
	leaders = week_role_leaders(week_id, fteams, session)
	lines2  = [f"```\n{SEP}", " TOP PERFORMERS BY ROLE", SEP]
	for role in ["IGL", "Duelist", "Initiator", "Controller", "Sentinel", "Flex"]:
		lines2.append(f" {role}")
		players = leaders.get(role, [])
		if not players:
			lines2.append("   —")
		for i, p in enumerate(players, 1):
			lines2.append(f"  {i}. {p['player']:<16} {p['pro_team']:<6} {p['fteam']:<5} {p['total']:>6.1f}")
	lines2.append(f"{SEP}```")
	msg2 = "\n".join(lines2)

	# ── Section 3: Top Base Scorers (incl. free agents) ────────
	scorers = week_top_base_scorers(week_id, fteams, session)
	lines3  = [f"```\n{SEP}", " TOP BASE SCORERS (incl. free agents)", SEP]
	for i, p in enumerate(scorers, 1):
		tag = f"({p['fteam']})" if p["fteam"] else "(FA)"
		lines3.append(f"  {i}. {p['player']:<16} {p['pro_team']:<6} {p['base']:>6.1f}  {tag}")
	lines3.append(f"{SEP}```")
	msg3 = "\n".join(lines3)

	return [msg1, msg2, msg3]


class MatchupCog(commands.Cog, name="Matchup"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Matchup cog: {error}")

	@commands.command()
	async def newseason(self, ctx, name: str, num_weeks: int, event_url: str = None):
		"""Create a new season. event_url is optional and can be added later with !seteventurl."""
		if event_url:
			try:
				Scraper.parse_event_page(event_url)
			except Exception as e:
				return await ctx.send(f"Failed to parse event page: {e}")

		with self.bot.db_manager.create_session() as session:
			existing = session.scalars(select(db.Season).where(db.Season.is_active == True)).all()
			for s in existing:
				s.is_active = False

			season = db.Season(name=name, event_url=event_url, num_weeks=num_weeks, is_active=True)
			session.add(season)
			session.flush()

			for i in range(1, num_weeks + 1):
				session.add(db.Week(season_id=season.id, week_number=i))

			if event_url:
				session.add(db.SeasonEvent(season_id=season.id, event_url=event_url))

			session.commit()

		url_note = "" if event_url else " No event URL set — use `!seteventurl <url>` when available."
		await ctx.send(f"Season created: **{name}** ({num_weeks} weeks). Use `!generateschedule` to build matchups.{url_note}")

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
			num_weeks = season.num_weeks
			# Compute round offset for stage continuation
			round_offset = 0
			if season.previous_season_id is not None:
				chain = get_season_chain(season)
				total_prev_weeks = sum(s.num_weeks for s in chain[:-1])
				round_offset = compute_round_offset(total_prev_weeks, len(team_ids))
			schedule = generate_schedule(team_ids, num_weeks, round_offset)

			for week_idx, pairs in enumerate(schedule):
				week_number = week_idx + 1
				week_id = week_map.get(week_number)
				if not week_id:
					continue
				for home_id, away_id, ghost_mirror_id in pairs:
					session.add(db.Matchup(
						week_id=week_id,
						home_team_id=home_id,
						away_team_id=away_id,
						ghost_team_id=ghost_mirror_id,
						home_score=0.0,
						away_score=0.0
					))

			session.commit()

		team_count = len(fteams)
		await ctx.send(f"Schedule generated for {team_count} teams across {num_weeks} weeks.")

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
				elif matchup.ghost_team_id is not None:
					matchup.away_score = compute_weekly_score(matchup.ghost_team_id, week.id, session)
				else:
					matchup.away_score = 0.0

			season.roster_locked = False
			session.commit()

			fteams = list(session.scalars(select(db.FantasyTeam)))
			summary_msgs = _fmt_week_summary(week_number, matchups, week.id, fteams, session)

		await ctx.send(f"Week {week_number} scores locked. Rosters are now unlocked.")
		for msg in summary_msgs:
			await ctx.send(msg)

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
			if away_team:
				away_score = compute_weekly_score(away_team.id, target_week.id, session)
			elif matchup_row.ghost_team_id is not None:
				away_score = compute_weekly_score(matchup_row.ghost_team_id, target_week.id, session)
			else:
				away_score = 0.0

			buf = f"```\nWeek {target_week.week_number} Matchup — {season.name}\n"
			buf += f"{home_team.abbrev} / {home_team.name}: {home_score} pts\n"
			if away_team:
				buf += f"{away_team.abbrev} / {away_team.name}: {away_score} pts\n"
			elif matchup_row.ghost_team:
				buf += f"{matchup_row.ghost_team.abbrev} Ghost: {away_score} pts\n"
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
					if m.away_team:
						away_label = m.away_team.abbrev
					elif m.ghost_team:
						away_label = f"{m.ghost_team.abbrev} Ghost"
					else:
						away_label = "Ghost"
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
	async def continueseason(self, ctx, name: str, num_weeks: int, event_url: str = None):
		"""Continue into a new stage (same teams, cumulative record). event_url optional."""
		if event_url:
			try:
				Scraper.parse_event_page(event_url)
			except Exception as e:
				return await ctx.send(f"Failed to parse event page: {e}")

		with self.bot.db_manager.create_session() as session:
			prev_season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not prev_season:
				return await ctx.send("No active season to continue from.")

			prev_id = prev_season.id
			prev_season.is_active = False

			new_season = db.Season(
				name=name,
				event_url=event_url,
				num_weeks=num_weeks,
				is_active=True,
				previous_season_id=prev_id,
			)
			session.add(new_season)
			session.flush()

			for i in range(1, num_weeks + 1):
				session.add(db.Week(season_id=new_season.id, week_number=i))

			if event_url:
				session.add(db.SeasonEvent(season_id=new_season.id, event_url=event_url))

			session.commit()

		url_note = "" if event_url else " No event URL set — use `!seteventurl <url>` when available."
		await ctx.send(
			f"Season continued: **{name}** ({num_weeks} weeks). "
			f"Run `!generateschedule` to build matchups (round offset applied automatically).{url_note}"
		)

	@commands.command()
	async def seteventurl(self, ctx, event_url: str):
		"""Attach a vlr.gg event URL to the active season (use when page becomes available)."""
		try:
			Scraper.parse_event_page(event_url)
		except Exception as e:
			return await ctx.send(f"Failed to parse event page: {e}")

		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			season.event_url = event_url

			existing = session.scalars(
				select(db.SeasonEvent).where(
					db.SeasonEvent.season_id == season.id,
					db.SeasonEvent.event_url == event_url,
				)
			).first()
			if not existing:
				session.add(db.SeasonEvent(season_id=season.id, event_url=event_url))

			session.commit()

		await ctx.send(f"Event URL set for **{season.name}**.")

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
