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


def add_spaces(buff, length):
	"""Add spaces until the buffer is at least the provided length."""
	rv = ""
	while (len(buff) + len(rv)) < length:
		rv += " "
	return rv
