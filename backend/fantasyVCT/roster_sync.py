"""
vlr.gg Roster Sync — polls team pages from the active season's events once per day
and keeps player statuses and team assignments current in the database.

Status values: 'active', 'reserve', 'inactive', 'teamless'
  - teamless = player absent from all tracked team pages; team_id set to NULL
"""
import asyncio
import datetime

from discord.ext import tasks, commands
from sqlalchemy import select

import fantasyVCT.database as db
from fantasyVCT.scraper import Scraper
from fantasyVCT.utils import normalize_handle


def _fetch_roster_data(event_urls: list[str]) -> tuple[dict[str, dict], dict[str, db.Team.__class__]]:
	"""Scrape all team pages from the given event URLs.

	Returns:
	    roster_by_handle: normalized_handle -> {name, status, team_name, team_abbrev}
	    teams_scraped:    team_name (upper) -> {name, abbrev}
	"""
	seen_team_urls: set[str] = set()
	roster_by_handle: dict[str, dict] = {}
	teams_scraped: dict[str, dict] = {}

	for event_url in event_urls:
		try:
			team_urls = Scraper.parse_event_teams(event_url)
		except Exception as e:
			print(f"[RosterSync] Failed to fetch event {event_url}: {e}")
			continue

		for url in team_urls:
			if url in seen_team_urls:
				continue
			seen_team_urls.add(url)
			try:
				team_name, team_abbrev, players = Scraper.parse_team_roster(url)
			except Exception as e:
				print(f"[RosterSync] Failed to scrape {url}: {e}")
				continue

			teams_scraped[team_name.upper()] = {"name": team_name, "abbrev": team_abbrev}

			for p in players:
				norm = normalize_handle(p["name"])
				roster_by_handle[norm] = {
					"name": p["name"],
					"status": p["status"],
					"team_name": team_name,
					"team_abbrev": team_abbrev,
				}

	print(f"[RosterSync] Scraped {len(teams_scraped)} teams, {len(roster_by_handle)} players")
	return roster_by_handle, teams_scraped


def _sync_once(session, roster_by_handle: dict, teams_scraped: dict) -> dict:
	"""Apply scraped roster data to the database.

	Returns a summary dict with change counts.
	"""
	summary = {
		"status_changed": 0,
		"team_changed": 0,
		"added": 0,
		"teamless": 0,
		"skipped": 0,
	}

	all_teams = list(session.scalars(select(db.Team)))
	team_by_name = {t.name.upper(): t for t in all_teams}
	team_by_abbrev = {t.abbrev.upper(): t for t in all_teams}

	all_players = list(session.scalars(select(db.Player)))
	notifications = []

	for player in all_players:
		scraped = roster_by_handle.get(normalize_handle(player.name))

		if scraped is None:
			# Player absent from all team pages → teamless
			if player.status != "teamless":
				old_status = player.status
				player.status = "teamless"
				player.team_id = None
				summary["teamless"] += 1
				print(f"[RosterSync] {player.name}: {old_status} → teamless (absent from all team pages)")
				fp = player.fantasyplayer
				if fp and fp.fantasy_team_id:
					manager = fp.fantasyteam.user
					notifications.append((
						f"<@{manager.discord_id}>" if manager else "(unknown)",
						player.name,
						"no team",
						"is no longer on any active roster",
					))
			continue

		new_status = scraped["status"]
		new_team = (
			team_by_name.get(scraped["team_name"].upper())
			or team_by_abbrev.get(scraped["team_abbrev"].upper())
		)

		# Status change
		if player.status != new_status:
			old_status = player.status
			player.status = new_status
			summary["status_changed"] += 1
			print(f"[RosterSync] {player.name}: status {old_status} → {new_status}")
			fp = player.fantasyplayer
			if fp and fp.fantasy_team_id:
				manager = fp.fantasyteam.user
				notifications.append((
					f"<@{manager.discord_id}>" if manager else "(unknown)",
					player.name,
					player.team.abbrev if player.team else "?",
					f"has moved to **{new_status.title()}** status",
				))

		# Team transfer
		if new_team and player.team_id != new_team.id:
			old_abbrev = player.team.abbrev if player.team else "?"
			player.team = new_team
			summary["team_changed"] += 1
			print(f"[RosterSync] {player.name}: team {old_abbrev} → {new_team.abbrev}")
			fp = player.fantasyplayer
			if fp and fp.fantasy_team_id:
				manager = fp.fantasyteam.user
				notifications.append((
					f"<@{manager.discord_id}>" if manager else "(unknown)",
					player.name,
					new_team.abbrev,
					f"has transferred to **{new_team.name}**",
				))

	# New active players not yet in DB
	db_handles = {normalize_handle(p.name) for p in all_players}
	for norm, scraped in roster_by_handle.items():
		if norm in db_handles:
			continue
		if scraped["status"] != "active":
			continue
		new_team = (
			team_by_name.get(scraped["team_name"].upper())
			or team_by_abbrev.get(scraped["team_abbrev"].upper())
		)
		if new_team:
			session.add(db.Player(name=scraped["name"], team=new_team, status="active"))
			summary["added"] += 1
			print(f"[RosterSync] Added new player: {scraped['name']} ({new_team.abbrev})")
		else:
			summary["skipped"] += 1
			print(f"[RosterSync] Skipped {scraped['name']} — team '{scraped['team_name']}' not in DB")

	session.commit()

	if notifications:
		summary["_notifications"] = notifications

	return summary


class RosterSyncCog(commands.Cog, name="RosterSync"):
	def __init__(self, bot):
		self.bot = bot
		self.sync_roster.start()

	def cog_unload(self):
		self.sync_roster.cancel()

	async def cog_command_error(self, ctx, error):
		await ctx.send(f"An error occurred in the RosterSync cog: {error}")

	def _get_event_urls(self) -> list[str]:
		"""Return event URLs from the active season."""
		with self.bot.db_manager.create_session() as session:
			season = session.scalars(
				select(db.Season).where(db.Season.is_active == True)
			).first()
			if not season:
				return []
			return [se.event_url for se in season.season_event_urls]

	async def _run_sync(self) -> tuple[dict, list, object]:
		"""Fetch roster data and run sync in thread executor."""
		event_urls = self._get_event_urls()
		if not event_urls:
			print("[RosterSync] No active season or event URLs — skipping")
			return {"status_changed": 0, "team_changed": 0, "added": 0, "teamless": 0, "skipped": 0}, [], None

		loop = asyncio.get_event_loop()
		roster_by_handle, teams_scraped = await loop.run_in_executor(
			None, _fetch_roster_data, event_urls
		)

		channel_id = self.bot.db_manager.get_config("gcd_notify_channel")
		notify_channel = self.bot.get_channel(int(channel_id)) if channel_id else None

		with self.bot.db_manager.create_session() as session:
			summary = _sync_once(session, roster_by_handle, teams_scraped)

		notifications = summary.pop("_notifications", [])
		return summary, notifications, notify_channel

	async def _dispatch_notifications(self, notifications, notify_channel):
		if not notify_channel or not notifications:
			return
		for mention, player_name, team_abbrev, change_msg in notifications:
			msg = f"⚠️ {mention} — your player **{player_name}** ({team_abbrev}) {change_msg}. Check your roster with `!roster`."
			await notify_channel.send(msg)
			await asyncio.sleep(1)

	@tasks.loop(hours=24)
	async def sync_roster(self):
		ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
		print(f"[RosterSync] Starting scheduled sync at {ts}")
		try:
			summary, notifications, notify_channel = await self._run_sync()
			print(f"[RosterSync] Done — {summary}")
			await self._dispatch_notifications(notifications, notify_channel)
		except Exception as e:
			print(f"[RosterSync] Sync failed: {e}")

	@sync_roster.before_loop
	async def before_sync_roster(self):
		await self.bot.wait_until_ready()

	@commands.command()
	@commands.has_permissions(administrator=True)
	async def syncroster(self, ctx):
		"""Manually trigger a vlr.gg roster sync (admin only).

		Scrapes all team pages from the active season's events and updates player
		statuses, team assignments, and notifies managers of any changes.
		"""
		await ctx.send("Running roster sync...")
		try:
			summary, notifications, notify_channel = await self._run_sync()
			await self._dispatch_notifications(notifications, notify_channel)
			await ctx.send(
				f"Roster sync complete — "
				f"{summary['status_changed']} status change(s), "
				f"{summary['team_changed']} transfer(s), "
				f"{summary['teamless']} player(s) marked teamless, "
				f"{summary['added']} new player(s) added, "
				f"{summary['skipped']} skipped (team not in DB)."
			)
		except Exception as e:
			await ctx.send(f"Roster sync failed: {e}")


async def setup(bot):
	await bot.add_cog(RosterSyncCog(bot))
