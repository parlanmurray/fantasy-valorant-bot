from fantasyVCT.scraper import Scraper

# unit testing

def test_map_names(maps):
	assert maps[0].name == "Haven"
	assert maps[1].name == "Breeze"
	assert maps[2].name == "Ascent"

def test_map_played(maps):
	assert maps[0].was_played == True
	assert maps[2].was_played == False

def test_map_number(maps):
	assert maps[0].number is 1

def main():
	scraper = Scraper()
	results = scraper.parse_match(25206)

	# Map
	test_map_names(results)
	test_map_played(results)

	# Team

	# Player

	print("All tests passed.")

if __name__ == "__main__":
	main()
