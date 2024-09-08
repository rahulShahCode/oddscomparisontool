import requests
import datetime

api_key = '340b5c9e6341113ad1e44792b3c83d0f'
sport = 'baseball_kbo'
market = 'h2h,spreads,totals'
bookmaker = 'pinnacle'
date_format = "%Y-%m-%dT%H:%M:%SZ"
start_timestamp = datetime.datetime(2024, 8, 1, 14, 45, 0)

def fetch_odds():
    url = f"https://api.the-odds-api.com/v4/historical/sports/{sport}/odds"
    params = {
        'apiKey': api_key,
        'markets': market,
        'bookmakers' : bookmaker,
        'date': '2024-08-01T15:15:37Z',
        'oddsFormat' : 'american'
    }
    response = requests.get(url, params=params)
    return response.json()

def find_event_id():
    current_timestamp = start_timestamp.strftime(date_format)
    while True:
        data = fetch_odds()
        for event in data['data']:
            if event['id'] == '1f57bff33684fe4542d7909897662346':
                return current_timestamp, event
        current_timestamp = data['next_timestamp']

timestamp, event = find_event_id()

