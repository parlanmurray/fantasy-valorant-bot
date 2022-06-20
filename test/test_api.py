from fantasyVCT.vlr_api import get_results

# unit testing
# run with pytest

def test_results):
	json = get_results()
	assert json['data']
	assert json['data']['status'] == 200
	assert json['data']['segments']
	assert json['data']['segments'][0]['match_page']
