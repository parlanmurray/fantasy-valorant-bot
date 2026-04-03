import re
import unicodedata


def normalize_handle(s: str) -> str:
	"""Normalize a player handle for fuzzy lookup.

	Strips spaces, hyphens, underscores, and dots; applies NFKD unicode
	decomposition; lowercases. Covers mismatches like 'luk xo' vs 'lukxo'
	and encoding differences like 'Rosé' vs 'Rose'.
	"""
	s = unicodedata.normalize('NFKD', s)
	s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
	s = re.sub(r'[\s\-_.]', '', s)
	return s.lower()


def find_player_by_name(session, name: str):
	"""Find a Player by name, with normalized fallback.

	Tries exact match first, then normalized match (strips spaces/punctuation/accents).
	Returns None if not found.
	"""
	from sqlalchemy import select
	import fantasyVCT.database as db

	player = session.execute(select(db.Player).filter_by(name=name)).scalar_one_or_none()
	if player:
		return player

	norm = normalize_handle(name)
	for p in session.scalars(select(db.Player)).all():
		if normalize_handle(p.name) == norm:
			return p
	return None


POSITIONS = {
	0: "IGL",
	1: "Duelist",
	2: "Initiator",
	3: "Controller",
	4: "Sentinel",
	5: "Flex",
	6: "Sub1",
	7: "Sub2",
	8: "Sub3",
	9: "Sub4"
}


def is_roster_locked(session) -> bool:
	"""Return True if the active season has rosters locked, False otherwise."""
	from sqlalchemy import select
	import fantasyVCT.database as db
	season = session.scalars(select(db.Season).where(db.Season.is_active == True)).first()
	return bool(season and season.roster_locked)
