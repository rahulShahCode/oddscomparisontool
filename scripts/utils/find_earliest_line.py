import requests 
import os 
import json 
import pandas as pd 

api_key = os.getenv('THE_ODDS_API_KEY')

sport_key = 'basketball_ncaab'

url = f'https://api.the-odds-api.com/v4/historical/sports/{sport_key}/odds'
start_date = '2024-03-18T00:00:00Z'
params = {
"apiKey": api_key,
"bookmakers": "betopenly",
"markets": "h2h",
"oddsFormat": "decimal",
"date": start_date
}
response = requests.get(url, params=params)

print(response.json())