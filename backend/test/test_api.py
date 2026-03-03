from fantasyVCT.scraper import Scraper
from fantasyVCT.vlr_api import vlr_api

import requests

# Integration tests against the live vlrggapi.vercel.app API.
# run with pytest

def test_health():
	r = requests.get(vlr_api.format("health"))
	assert r.status_code == 200
	json = r.json()
	assert json['service']['status'] == "Healthy"

def test_request_200():
	assert requests.get(vlr_api.format("v2/match?q=results&num_pages=1")).status_code == 200

def test_results():
	json = requests.get(vlr_api.format("v2/match?q=results&num_pages=1")).json()
	assert json['data']
	assert json['data']['segments']
	assert json['data']['segments'][0]['match_page']

def test_scrape_resutls():
	scraper = Scraper()
	json = requests.get(vlr_api.format("v2/match?q=results&num_pages=1")).json()

	for game in json['data']['segments']:
		vlr_id = game['match_page'].split('/')[1]
		scraper.parse_match(vlr_id)

	assert True
