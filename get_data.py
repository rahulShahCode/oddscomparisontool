from flask import Flask, render_template
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

def decimal_to_american(odds):
    if odds > 2.0:
        return f"+{int((odds - 1) * 100)}"
    elif odds == 2.0:
        return "+100"
    else:
        return str(int(-100 / (odds - 1)))

def format_datetime(timestamp):
    utc_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
    est_time = utc_time - timedelta(hours=5)  # Adjust for Eastern Standard Time
    return est_time.strftime('%B %d, %Y %H:%M')

def process_games(games):
    for game in games:
        game['commence_time'] = format_datetime(game['commence_time'])
        game['markets'] = {}
        fanduel_markets = {market['key']: market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'fanduel' for market in bookmaker['markets']}
        pinnacle_markets = {market['key']: market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'pinnacle' for market in bookmaker['markets']}
        
        for market_key in ['h2h', 'spreads', 'totals']:
            if market_key in fanduel_markets and market_key in pinnacle_markets:
                fanduel_data = fanduel_markets[market_key]
                pinnacle_data = pinnacle_markets[market_key]
                market_display = {'fanduel': [], 'pinnacle': []}
                for f_outcome, p_outcome in zip(fanduel_data['outcomes'], pinnacle_data['outcomes']):
                    f_price = f_outcome['price']
                    p_price = p_outcome['price']
                    f_american = decimal_to_american(f_price)
                    p_american = decimal_to_american(p_price)
                    
                    display_name = f_outcome['name']
                    if market_key != 'h2h':
                        display_name += f" {f_outcome.get('point', '')}"
                    
                    market_display['fanduel'].append((display_name, f_american))
                    market_display['pinnacle'].append((display_name, p_american))

                game['markets'][market_key if market_key != 'h2h' else 'moneyline'] = market_display

    return games

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
    processed_games = process_games(games)

    return render_template('odds.html', games=processed_games)

if __name__ == '__main__':
    app.run(debug=True)
