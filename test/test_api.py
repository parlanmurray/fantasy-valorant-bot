from fantasyVCT.scraper import Scraper

import requests

# unit testing
# run with pytest

vlr_api = "https://vlrggapi.herokuapp.com/{}"

def test_request_200():
	assert requests.get(vlr_api.format("match/results")).status_code == 200

def test_results():
	json = requests.get(vlr_api.format("match/results")).json()
	assert json['data']
	assert json['data']['status'] == 200
	assert json['data']['segments']
	assert json['data']['segments'][0]['match_page']

def test_scrape_resutls():
	scraper = Scraper()
	json = requests.get(vlr_api.format("match/results")).json()

	for game in json['data']['segments']:
		vlr_id = game['match_page'].split('/')[1]
		scraper.parse_match(vlr_id)

	assert True
