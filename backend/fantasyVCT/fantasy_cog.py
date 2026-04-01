import typing

import fantasyVCT.database as db

from discord.ext import commands
import discord
from sqlalchemy import select, or_

from fantasyVCT.scoring import PointCalculator
from fantasyVCT.matchup import compute_weekly_score, derive_record, get_season_chain, player_week_totals
from fantasyVCT.utils import POSITIONS, is_roster_locked


class FantasyCog(commands.Cog, name="Fantasy"):
	def __init__(self, bot):
		self.bot = bot
		self.pos_max = min(10, 6 + bot.sub_slots)

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the Fantasy cog: {error}")

	@commands.command()
	async def draft(self, ctx, player_name: str):
		"""Pick a player during the draft or add a free agent to your roster.

		Parameters:
		-----------
		player_name: Player's exact IGN (case-sensitive). Use !freeagents to see available players.
		"""
		author_id = ctx.message.author.id

		if not self.bot.draft_state.is_draft_started():
			return await ctx.send("Draft has not started yet!")
		elif not self.bot.draft_state.can_draft(author_id):
			return await ctx.send("It is not your turn yet!")

		with self.bot.db_manager.create_session() as session:
			if self.bot.draft_state.is_draft_complete() and is_roster_locked(session):
				return await ctx.send("Rosters are locked for the current week. Wait for !closeweek to unlock.")

			drafted_player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
			if not drafted_player:
				return await ctx.send(f"No player was found for \"{player_name}\"")

			if drafted_player.fantasyplayer:
				return await ctx.send(f"{drafted_player.name} has already been drafted to a fantasy team.")

			user = session.execute(select(db.User).filter_by(discord_id=author_id)).scalar_one_or_none()
			if not user:
				return await ctx.send("You are not registered. Please use the `!register` command to register. Type `!help` for more informaiton.")
			elif not user.fantasyteam:
				return await ctx.send("You do not have a fantasy team. Please use the `!register` command to create a fantasy team. Type `!help` for more information.")

			drafted_fp = None
			sub_flag = False
			placed_flag = False
			for i in range(self.pos_max):
				if sub_flag and i < 6:
					continue
				skip_flag = False
				for fp in user.fantasyteam.fantasyplayers:
					if fp.position == i:
						# IGL–Sentinel (0–4) are team-restricted; Flex (5) is not
						if i < 5 and drafted_player.team and fp.player.team == drafted_player.team:
							sub_flag = True
						skip_flag = True
						break

				if skip_flag or drafted_fp:
					continue

				drafted_fp = db.FantasyPlayer(position=i)
				drafted_fp.player = drafted_player
				drafted_fp.fantasyteam = user.fantasyteam
				session.add(drafted_fp)

				session.flush()
				session.commit()
				placed_flag = True
				break

		if placed_flag:
			await ctx.invoke(self.bot.get_command('roster'))

			if self.bot.draft_state.is_draft_started() and not self.bot.draft_state.is_draft_complete():
				next_drafter = self.bot.draft_state.next()
				if next_drafter:
					await ctx.send(f"It is <@!{next_drafter}>'s turn to draft!")
				else:
					await ctx.send("Initial draft is complete!")
			return

		return await ctx.send("You do not have a spot for this player on your roster. Use `!drop` if you want to make space. Type `!help` for more information.")

	@commands.command()
	async def drop(self, ctx, player_name: str):
		"""Release a player from your roster back to free agency.

		Parameters:
		-----------
		player_name: Player's exact IGN (case-sensitive). Use !roster to see your current players.
		"""
		author_id = ctx.message.author.id

		if not self.bot.draft_state.is_draft_complete():
			return await ctx.send("Cannot drop players until initial draft is complete.")

		with self.bot.db_manager.create_session() as session:
			if is_roster_locked(session):
				return await ctx.send("Rosters are locked for the current week. Wait for !closeweek to unlock.")
			dropped_player = session.execute(select(db.Player).filter_by(name=player_name)).scalar_one_or_none()
			if not dropped_player:
				return await ctx.send(f"No player was found for \"{player_name}\"")

			user = session.execute(select(db.User).filter_by(discord_id=author_id)).scalar_one_or_none()
			if not dropped_player.fantasyplayer or dropped_player.fantasyplayer not in user.fantasyteam.fantasyplayers:
				return await ctx.send(f"No player {dropped_player.name} found on your roster. Try the `!roster` command. Type `!help` for more information.")

			session.delete(dropped_player.fantasyplayer)
			session.flush()
			session.commit()

			await ctx.send(f"{dropped_player.name} is now a free agent!")

	@commands.command()
	async def roster(self, ctx, member: typing.Optional[discord.Member] = None, team: typing.Optional[str] = None):
		"""Display a fantasy team's roster and points. Defaults to your own team.

		Parameters:
		-----------
		member: @mention a Discord user to view their roster (optional).
		team: Team abbreviation or name to view (optional).
		"""

		with self.bot.db_manager.create_session() as session:
			fantasy_team = None

			if member:
				user = session.execute(select(db.User).filter_by(discord_id=member.id)).scalar_one_or_none()
				if not user or not user.fantasyteam:
					return await ctx.send(f"{member.name} does not have a registered fantasy team.")
				fantasy_team = user.fantasyteam
			elif team:
				fantasy_team = session.execute(select(db.FantasyTeam).where(
					or_(
						db.FantasyTeam.name == team,
						db.FantasyTeam.abbrev == team
					)
				)).scalar_one_or_none()
				if not fantasy_team:
					return await ctx.send(f"No fantasy team found for {team}")
			else:
				author = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
				if not author or not author.fantasyteam:
					return await ctx.send("You do not have a registered fantasy team. Use the `!register` command. Type `!help` for more information.")
				fantasy_team = author.fantasyteam

			fantasy_players = fantasy_team.fantasyplayers

			# Resolve current display week: first week with results, or most recent
			week_id = None
			week_label = ""
			active_season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if active_season:
				weeks = sorted(active_season.weeks, key=lambda w: w.week_number)
				current_week = None
				for w in weeks:
					has_results = session.scalars(select(db.Result).where(db.Result.week_id == w.id)).first()
					if has_results:
						current_week = w
				if current_week:
					week_id = current_week.id
					week_label = f"  [Week {current_week.week_number}]"

			SEP = "  " + "─" * 38
			buf = "```\n" + fantasy_team.abbrev + " / " + fantasy_team.name
			total = 0
			buf2 = ""
			for k in range(self.pos_max):
				line = f"  {POSITIONS[k]}"
				for fp in fantasy_players:
					if fp.position is k:
						line = f"{line:<14}{fp.player.team.abbrev} {fp.player.name}"
						if week_id is not None and k < 6:
							base_pts, role_pts, _ = player_week_totals(fp.player_id, k, week_id, session)
						else:
							base_pts, role_pts = 0.0, 0.0
						if k < 6:
							total += round(base_pts + role_pts, 1)
						line = f"{line:<30}{base_pts}"
						if k < 6:
							line = f"{line:<36}{role_pts}"
						break
				buf2 += line + "\n"
				if k == 5:
					buf2 += SEP + "\n"
			buf += " -- " + str(round(total, 1)) + week_label + "\n"
			line = f"  {'Role':<12}Player"
			line = f"{line:<30}Base"
			line = f"{line:<36}Bonus"
			buf += line + "\n"
			buf += SEP + "\n"
			buf += buf2 + "```"
			await ctx.send(buf)

	@commands.command()
	async def freeagents(self, ctx):
		"""List all undrafted players grouped by pro team, sorted by PPG."""

		with self.bot.db_manager.create_session() as session:
			stmt = (
				select(db.Player)
				.where(db.Player.id.notin_(select(db.FantasyPlayer.player_id)))
				.where(db.Player.team_id.isnot(None))
			)
			free_agents = list(session.scalars(stmt))

			# Group by team, compute PPG per player
			teams: dict[str, list[tuple[str, float]]] = {}
			for player in free_agents:
				team_name = player.team.name if player.team else "Unknown"
				num_maps = len(player.results)
				if num_maps > 0:
					total = sum(PointCalculator.score(r) for r in player.results)
					ppg = round(total / num_maps, 1)
				else:
					ppg = None
				teams.setdefault(team_name, []).append((player.name, ppg))

			# Sort teams alphabetically; within each team sort by PPG desc (None last)
			RULE = "─" * 30
			messages = []
			buf = f"```\nFree Agents\n{RULE}\n"
			for team_name in sorted(teams):
				players = sorted(teams[team_name], key=lambda x: x[1] if x[1] is not None else -1, reverse=True)
				team_block = f" {team_name}\n"
				for name, ppg in players:
					ppg_str = f"{ppg}" if ppg is not None else "--"
					team_block += f"   {name:<18}{ppg_str}\n"
				team_block += "\n"

				# Flush if adding this block would exceed limit
				if len(buf + team_block) > 1900:
					buf += f"{RULE}```"
					messages.append(buf)
					buf = f"```\nFree Agents (cont.)\n{RULE}\n"
				buf += team_block

			buf += f"{RULE}```"
			messages.append(buf)

		for msg in messages:
			await ctx.send(msg)

	@commands.command()
	async def set(self, ctx, player: str, position: str):
		"""Move a player to a different position on your roster.

		Parameters:
		-----------
		player: Player's exact IGN (case-sensitive).
		position: Target role (igl, duelist, initiator, controller, sentinel, flex, sub1–sub4).
		"""

		with self.bot.db_manager.create_session() as session:
			if is_roster_locked(session):
				return await ctx.send("Rosters are locked for the current week. Wait for !closeweek to unlock.")

		if not position.lower() in (string.lower() for string in POSITIONS.values()):
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")
		dest_pos = list(POSITIONS.keys())[list(string.lower() for string in POSITIONS.values()).index(position.lower())]
		if dest_pos >= self.pos_max:
			return await ctx.send("Not a valid position. Try command `!roster`. Type `!help` for more information.")

		with self.bot.db_manager.create_session() as session:
			set_player = session.execute(select(db.Player).filter_by(name=player)).scalar_one_or_none()
			if not set_player:
				return await ctx.send(f"No player was not found for \"{player}\".")

			user = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
			if set_player.fantasyplayer not in user.fantasyteam.fantasyplayers:
				return await ctx.send(f"{set_player.name} is not on your roster.")

			dest_player = session.execute(select(db.FantasyPlayer).filter_by(fantasy_team_id=user.fantasy_team_id, position=dest_pos)).scalar_one_or_none()
			if dest_player:
				dest_player.position = set_player.fantasyplayer.position
				set_player.fantasyplayer.position = dest_pos
			else:
				set_player.fantasyplayer.position = dest_pos

			# IGL–Sentinel (0–4) are team-restricted; Flex (5) is not
			existing_teams = list()
			for curr_player in user.fantasyteam.fantasyplayers:
				if curr_player.position < 5:
					if curr_player.player.team in existing_teams:
						session.rollback()
						return await ctx.send("Cannot assign player to this position due to team restriction. See !rules.")
					else:
						existing_teams.append(curr_player.player.team)

			session.flush()
			session.commit()
			await ctx.invoke(self.bot.get_command('roster'))

	@commands.command()
	async def setall(self, ctx, igl: str, duelist: str, initiator: str, controller: str, sentinel: str, flex: str):
		"""Assign all 6 active slots at once. Remaining roster players fill sub slots.

		Parameters:
		-----------
		igl: Player IGN for the IGL slot.
		duelist: Player IGN for the Duelist slot.
		initiator: Player IGN for the Initiator slot.
		controller: Player IGN for the Controller slot.
		sentinel: Player IGN for the Sentinel slot.
		flex: Player IGN for the Flex slot.
		"""
		with self.bot.db_manager.create_session() as session:
			if is_roster_locked(session):
				return await ctx.send("Rosters are locked for the current week. Wait for !closeweek to unlock.")

			user = session.execute(select(db.User).filter_by(discord_id=ctx.message.author.id)).scalar_one_or_none()
			if not user or not user.fantasyteam:
				return await ctx.send("You do not have a registered fantasy team.")

			names = [igl, duelist, initiator, controller, sentinel, flex]

			# Validate no duplicates
			seen = set()
			for name in names:
				if name in seen:
					return await ctx.send(f"Duplicate player: {name}. Each slot must be a different player.")
				seen.add(name)

			# Resolve players and validate all on roster
			fp_by_name = {fp.player.name: fp for fp in user.fantasyteam.fantasyplayers}
			resolved = []  # list of (position, FantasyPlayer) in slot order
			for pos, name in enumerate(names):
				if name not in fp_by_name:
					return await ctx.send(f"{name} is not on your roster.")
				resolved.append((pos, fp_by_name[name]))

			# Validate team restriction for positions 0–4
			seen_teams = {}
			for pos, fp in resolved[:5]:
				team = fp.player.team
				if team and team in seen_teams:
					other_name = seen_teams[team]
					return await ctx.send(
						f"Team restriction: {other_name} and {fp.player.name} are both on {team.name}. "
						f"IGL through Sentinel must be from different pro teams. See !rules."
					)
				seen_teams[team] = fp.player.name

			# Assign active slots 0–5
			assigned_ids = {fp.id for _, fp in resolved}
			for pos, fp in resolved:
				fp.position = pos

			# Fill subs with remaining players in their current position order
			subs = sorted(
				[fp for fp in user.fantasyteam.fantasyplayers if fp.id not in assigned_ids],
				key=lambda fp: fp.position
			)
			for sub_pos, fp in enumerate(subs, start=6):
				fp.position = sub_pos

			session.commit()
			await ctx.invoke(self.bot.get_command('roster'))

	@commands.command()
	async def standings(self, ctx):
		"""Show W/L/T standings and total points across all stages of the active season."""

		with self.bot.db_manager.create_session() as session:
			season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
			if not season:
				return await ctx.send("No active season.")

			chain = get_season_chain(season)
			all_season_ids = [s.id for s in chain]
			all_weeks = [wk for s in chain for wk in s.weeks]

			fteams = list(session.scalars(select(db.FantasyTeam)))
			rows = []
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
				total_pts = round(sum(compute_weekly_score(fteam.id, wk.id, session) for wk in all_weeks), 1)
				rows.append((fteam, w, l, t, total_pts))

			rows.sort(key=lambda r: (-r[1], -r[4]))

			names = [f"{fteam.abbrev} / {fteam.name}" for fteam, *_ in rows]
			col_w = max(len(n) for n in names) if names else 18
			col_w = max(col_w, len("Team"))

			buf = "```\nStandings\n\n"
			buf += f"  {'Team':<{col_w}}  W  L  T  Pts\n"
			for (fteam, w, l, t, pts), name in zip(rows, names):
				buf += f"  {name:<{col_w}}  {w:<3}{l:<3}{t:<3}{pts}\n"
			buf += "```"
			await ctx.send(buf)


async def setup(bot):
	await bot.add_cog(FantasyCog(bot))
