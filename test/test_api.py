import requests

# unit testing
# run with pytest

vlr_api = "https://vlrggapi.herokuapp.com/{}"

def test_results():
	json = requests.get(vlr_api.format("match/results")).json()
	assert json['data']
	assert json['data']['status'] == 200
	assert json['data']['segments']
	assert json['data']['segments'][0]['match_page']
