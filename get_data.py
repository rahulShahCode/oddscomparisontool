from flask import Flask, render_template
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

def decimal_to_american(odds):
    """Converts decimal odds to American odds."""
    if odds >= 2.0:
        return int((odds - 1) * 100)
    else:
        return int(-100 / (odds - 1))

def format_datetime(timestamp):
    """Convert UTC to EST and format."""
    utc_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
    est_time = utc_time - timedelta(hours=5)  # Adjust for EST
    return est_time.strftime('%B %d, %Y %H:%M')

@app.route('/')
def home():
    api_key = os.getenv('THE_ODDS_API_KEY')
    if not api_key:
        return "API key not found. Please set the environment variable 'THE_ODDS_API_KEY'."

    url = 'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds'
    params = {
        "apiKey": api_key,
        "regions": 'us',
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return f"Failed to retrieve data: {response.status_code} - {response.text}"

    games = response.json()
    games = sorted(games, key=lambda x: x['commence_time'])  # Sort games by start time

    for game in games:
        game['commence_time'] = format_datetime(game['commence_time'])
        for bookmaker in game['bookmakers']:
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    price = outcome['price']
                    outcome['american_odds'] = decimal_to_american(price)

    return render_template('odds.html', games=games)

if __name__ == '__main__':
    app.run(debug=True)
