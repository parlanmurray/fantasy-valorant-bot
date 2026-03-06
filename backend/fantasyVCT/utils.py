POSITIONS = {
	0: "Captain",
	1: "Player1",
	2: "Player2",
	3: "Player3",
	4: "Player4",
	5: "Player5",
	6: "Sub1",
	7: "Sub2",
	8: "Sub3",
	9: "Sub4"
}


def add_spaces(buff, length):
	"""Add spaces until the buffer is at least the provided length."""
	rv = ""
	while (len(buff) + len(rv)) < length:
		rv += " "
	return rv
