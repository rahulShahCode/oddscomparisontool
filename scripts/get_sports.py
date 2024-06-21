import requests 
import os 
import json 
def get_active_sports(sports): 
    active_sports = [] 
    for sport in sports:
        if sport['active'] is True and sport['has_outrights'] is False: 
            active_sports.append(sport)
    return active_sports


url = "https://api.the-odds-api.com/v4/sports/"
api_key = os.getenv('THE_ODDS_API_KEY')
if not api_key:
    raise "API key not found. Please set the environment variable 'THE_ODDS_API_KEY'."
payload = {"apiKey" : api_key}

response = requests.get(url,params=payload)
active_sports = get_active_sports(response.json())
f = open('data/debug/active_sports.json', 'w')

json.dump(active_sports,f)