import requests

vlr_api = "https://vlrggapi.herokuapp.com/{}"

def get_results():
	r = requests.get(vlr_api.format("match/results"))
	if r.status_code != 200:
		raise RuntimeError
	return r.json()
