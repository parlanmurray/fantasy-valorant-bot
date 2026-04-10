import fantasyVCT.database as db
from fantasyVCT.scraper import Scraper
from fantasyVCT.matchup import (
	generate_schedule, compute_weekly_score, compute_weekly_score_snapshot,
	get_roster_breakdown, derive_record,
	get_season_chain, compute_round_offset,
	week_role_leaders, week_top_base_scorers, week_top_map_performances,
)

from discord.ext import commands
from sqlalchemy import select


def _fmt_week_summary(week_number: int, matchups: list, week_id: int, fteams: list, session) -> list[str]:
	"""Build week summary message strings (sections 1–4). Returns list of Discord messages."""
	SEP = "═" * 46

	# ── Section 1: Matchup Results ─────────────────────────────
	lines = [f"```\n{SEP}", f" WEEK {week_number} RESULTS", SEP]
	for m in matchups:
		home = m.home_team.abbrev
		hs   = m.home_score
		aws  = m.away_score
		if m.away_team_id is not None:
			away = m.away_team.abbrev
			w, ws, l, ls = (home, hs, away, aws) if hs >= aws else (away, aws, home, hs)
			lines.append(f" {w:<10} {ws:>6.1f}  defeats  {l:<10} {ls:>6.1f}")
		else:
			mirror = m.ghost_team.abbrev if m.ghost_team else "?"
			lines.append(f" {home:<10} {hs:>6.1f}  defeats  {'GHOST':<10} {aws:>6.1f}  (via {mirror})")
	lines.append(f"{SEP}```")
	msg1 = "\n".join(lines)

	# ── Section 2: Top Performers by Role ──────────────────────
	leaders    = week_role_leaders(week_id, fteams, session)
	all_p      = [p for role in leaders.values() for p in role]
	name_w     = max((len(f"{p['pro_team']} {p['player']}") for p in all_p), default=len("PLAYER"))
	name_w     = max(name_w, len("PLAYER"))
	team_w     = max((len(p['fteam']) for p in all_p), default=len("TEAM"))
	team_w     = max(team_w, len("TEAM"))
	lines2     = [f"```\n{SEP}", " TOP PERFORMERS BY ROLE", SEP]
	lines2.append(f"  #  {'PLAYER':<{name_w}} {'TEAM':<{team_w}}  {'BASE':>6}  {'BONUS':>6}  {'PTS':>6}")
	for role in ["IGL", "Duelist", "Initiator", "Controller", "Sentinel", "Flex"]:
		lines2.append(f" {role}")
		players = leaders.get(role, [])
		if not players:
			lines2.append("   —")
		for i, p in enumerate(players, 1):
			name = f"{p['pro_team']} {p['player']}"
			lines2.append(f"  {i}. {name:<{name_w}} {p['fteam']:<{team_w}}  {p['base']:>6.1f}  {p['bonus']:>6.1f}  {p['total']:>6.1f}")
	lines2.append(f"{SEP}```")
	msg2 = "\n".join(lines2)

	# ── Section 3: Top Base Scorers ────────────────────────────
	scorers = week_top_base_scorers(week_id, fteams, session)
	s_name_w = max((len(f"{p['pro_team']} {p['player']}") for p in scorers), default=len("PLAYER"))
	s_name_w = max(s_name_w, len("PLAYER"))
	s_team_w = max((len(p['fteam']) if p['fteam'] else 1 for p in scorers), default=len("TEAM"))
	s_team_w = max(s_team_w, len("TEAM"))
	lines3   = [f"```\n{SEP}", " TOP BASE SCORERS", SEP]
	lines3.append(f"  #  {'PLAYER':<{s_name_w}} {'TEAM':<{s_team_w}}  {'PTS':>6}")
	for i, p in enumerate(scorers, 1):
		name = f"{p['pro_team']} {p['player']}"
		tag  = p['fteam'] if p['fteam'] else "-"
		lines3.append(f"  {i}. {name:<{s_name_w}} {tag:<{s_team_w}}  {p['base']:>6.1f}")
	lines3.append(f"{SEP}```")
	msg3 = "\n".join(lines3)

	# ── Section 4: Top Map Performances ────────────────────────
	perfs  = week_top_map_performances(week_id, session)
	lines4 = [f"```\n{SEP}", " TOP MAP PERFORMANCES", SEP]
	if perfs:
		p_name_w = max(len(f"{p['pro_team']} {p['player']}") for p in perfs)
		p_name_w = max(p_name_w, len("PLAYER"))
		map_w    = max(len(p['map_str']) for p in perfs)
		map_w    = max(map_w, len("MAP"))
		k_w      = max(len(str(p['kills']))   for p in perfs); k_w = max(k_w, len("K"))
		d_w      = max(len(str(p['deaths']))  for p in perfs); d_w = max(d_w, len("D"))
		a_w      = max(len(str(p['assists'])) for p in perfs); a_w = max(a_w, len("A"))
		mk_w     = max(len(str(int(p['mk_pts']))) for p in perfs); mk_w = max(mk_w, len("MK/Clutch"))
		lines4.append(f"  #  {'PLAYER':<{p_name_w}} {'MAP':<{map_w}}  {'ACS':>4}  {'K':>{k_w}} {'D':>{d_w}} {'A':>{a_w}}  {'MK/Clutch':<{mk_w}}  {'PTS':>6}")
		for i, p in enumerate(perfs, 1):
			name = f"{p['pro_team']} {p['player']}"
			mk   = str(int(p['mk_pts']))
			lines4.append(
				f"  {i}. {name:<{p_name_w}} {p['map_str']:<{map_w}}  {p['acs']:>4.0f}  "
				f"{p['kills']:>{k_w}} {p['deaths']:>{d_w}} {p['assists']:>{a_w}}  {mk:<{mk_w}}  {p['base']:>6.1f}"
			)
	lines4.append(f"{SEP}```")
	msg4 = "\n".join(lines4)

	return [msg1, msg2, msg3, msg4]


class MatchupCog(commands.Cog, name="Matchup"):
	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Matchup cog: {error}")

	@commands.command()
	async def newseason(self, ctx, name: str, num_weeks: int):
		"""Create a new season. Add event URLs afterwards with !addevent.

		Parameters:
		-----------
		name: Name of the season (e.g. "VCT 2025 Americas Stage 1").
		num_weeks: Number of weeks to schedule.
		"""
		with self.bot.db_manager.create_session() as session:
			existing = session.scalars(select(db.Season).where(db.Season.is_active == True)).all()
			for s in existing:
				s.is_active = False

			season = db.Season(name=name, num_weeks=num_weeks, is_active=True)
			session.add(season)
			session.flush()

			for i in range(1, num_weeks + 1):
				session.add(db.Week(season_id=season.id, week_number=i))

			session.commit()

		await ctx.send(f"Season created: **{name}** ({num_weeks} weeks). Use `!addevent` to attach event URLs, then `!generateschedule` to build matchups.")

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
		"""Finalize scores for a given week and unlock rosters for the next week.

		Parameters:
		-----------
		week_number: The week number to close (e.g. 1).
		"""
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
				matchup.home_score = compute_weekly_score_snapshot(matchup.home_team_id, week.id, session)
				if matchup.away_team_id is not None:
					matchup.away_score = compute_weekly_score_snapshot(matchup.away_team_id, week.id, session)
				elif matchup.ghost_team_id is not None:
					matchup.away_score = compute_weekly_score_snapshot(matchup.ghost_team_id, week.id, session)
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
		"""Lock all rosters and snapshot current assignments for the upcoming week."""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			# Find the first week with no results yet (upcoming week to snapshot)
			target_week = None
			for w in sorted(season.weeks, key=lambda w: w.week_number):
				has_results = session.scalars(
					select(db.Result).where(db.Result.week_id == w.id)
				).first()
				if not has_results:
					target_week = w
					break

			if target_week is None:
				season.roster_locked = True
				session.commit()
				return await ctx.send("Rosters are now locked. (No upcoming week found — no snapshot taken.)")

			# Guard: skip if snapshot already exists for this week
			existing = session.scalars(
				select(db.RosterSnapshot).where(db.RosterSnapshot.week_id == target_week.id)
			).first()
			if existing:
				season.roster_locked = True
				session.commit()
				return await ctx.send(f"Rosters locked. Snapshot already exists for week {target_week.week_number} — not overwritten.")

			fteams = list(session.scalars(select(db.FantasyTeam)))
			player_count = 0
			for fteam in fteams:
				for fp in fteam.fantasyplayers:
					session.add(db.RosterSnapshot(
						week_id=target_week.id,
						fteam_id=fteam.id,
						player_id=fp.player_id,
						position=fp.position,
					))
					player_count += 1

			season.roster_locked = True
			session.commit()
			week_num = target_week.week_number
			team_count = len(fteams)

		await ctx.send(
			f"Rosters locked. Snapshot taken for week {week_num} "
			f"({team_count} teams, {player_count} players)."
		)

	@commands.command()
	async def matchup(self, ctx, week: int = None):
		"""Show your matchup for the current (or specified) week.

		Parameters:
		-----------
		week: Week number to view (optional, defaults to most recent week with results).
		"""
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

			home_score = matchup_row.home_score if matchup_row.home_score > 0 else compute_weekly_score_snapshot(home_team.id, target_week.id, session)
			if matchup_row.away_score > 0:
				away_score = matchup_row.away_score
			elif away_team:
				away_score = compute_weekly_score_snapshot(away_team.id, target_week.id, session)
			elif matchup_row.ghost_team_id is not None:
				away_score = compute_weekly_score_snapshot(matchup_row.ghost_team_id, target_week.id, session)
			else:
				away_score = 0.0

			label = "def" if home_score != away_score else "vs"

			away_display_team = away_team or matchup_row.ghost_team
			away_label = (
				f"{away_team.abbrev}" if away_team
				else f"{matchup_row.ghost_team.abbrev} Ghost" if matchup_row.ghost_team
				else "Ghost"
			)

			SEP = "═" * 42
			RULE = "─" * 40

			home_snap, home_slots = get_roster_breakdown(home_team.id, target_week.id, session)
			if away_display_team:
				away_snap, away_slots = get_roster_breakdown(away_display_team.id, target_week.id, session)
			else:
				away_snap, away_slots = False, []

			def fmt_team_block(team, abbrev, snap, slots):
				lines = [f" {abbrev} — {team.name}"]
				if not snap:
					lines.append("  (current roster — no snapshot)")
				lines.append(f"  {'Role':<11} {'Player':<16} {'Base':>5}  {'Bonus':>5}")
				lines.append(f"  {RULE}")
				active = [s for s in slots if s["is_active"]]
				for s in active:
					if s["player_name"] is None:
						lines.append(f"  {s['role']:<11} {'(empty)':<16}")
					else:
						lines.append(f"  {s['role']:<11} {s['player_name']:<16} {s['base']:>5.1f}  {s['bonus']:>5.1f}")
				return lines

			buf_lines = [
				"```",
				SEP,
				f" WEEK {target_week.week_number} — {season.name}",
				f" {home_team.abbrev} {home_score} - {away_score} {away_label}",
				SEP,
			]
			buf_lines += fmt_team_block(home_team, home_team.abbrev, home_snap, home_slots)
			buf_lines.append("")
			if away_display_team:
				buf_lines += fmt_team_block(away_display_team, away_label, away_snap, away_slots)
			buf_lines += [SEP, "```"]

			await ctx.send("\n".join(buf_lines))

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
	async def continueseason(self, ctx, name: str, num_weeks: int):
		"""Continue into a new stage with the same teams and cumulative record.

		Parameters:
		-----------
		name: Name of the new stage (e.g. "VCT 2025 Americas Stage 2").
		num_weeks: Number of weeks to schedule.
		"""
		with self.bot.db_manager.create_session() as session:
			prev_season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not prev_season:
				return await ctx.send("No active season to continue from.")

			prev_id = prev_season.id
			prev_season.is_active = False

			new_season = db.Season(
				name=name,
				num_weeks=num_weeks,
				is_active=True,
				previous_season_id=prev_id,
			)
			session.add(new_season)
			session.flush()

			for i in range(1, num_weeks + 1):
				session.add(db.Week(season_id=new_season.id, week_number=i))

			session.commit()

		await ctx.send(
			f"Season continued: **{name}** ({num_weeks} weeks). "
			f"Use `!addevent` to attach event URLs, then `!generateschedule` to build matchups (round offset applied automatically)."
		)

	@commands.command()
	async def seteventurl(self, ctx, event_url: str):
		"""Attach a vlr.gg event URL to the active season.

		Parameters:
		-----------
		event_url: vlr.gg event page URL (e.g. https://www.vlr.gg/event/2395/...).
		"""
		try:
			Scraper.parse_event_page(event_url)
		except Exception as e:
			return await ctx.send(f"Failed to parse event page: {e}")

		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			season_name = season.name

			existing = session.scalars(
				select(db.SeasonEvent).where(
					db.SeasonEvent.season_id == season.id,
					db.SeasonEvent.event_url == event_url,
				)
			).first()
			if not existing:
				session.add(db.SeasonEvent(season_id=season.id, event_url=event_url))

			session.commit()

		await ctx.send(f"Event URL set for **{season_name}**.")

	@commands.command()
	async def addevent(self, ctx, event_url: str):
		"""Add a regional event URL to the active season.

		Parameters:
		-----------
		event_url: vlr.gg event page URL for a regional sub-event (e.g. Americas, EMEA).
		"""
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
