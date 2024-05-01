from flask import Flask, render_template, request
import requests
import json 
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
    est_time = utc_time - timedelta(hours=4)  # Adjust for Eastern Daylight Time (EDT)
    return est_time.strftime('%B %d, %Y %I:%M %p')

def fetch_odds(sport_key):
    api_key = os.getenv('THE_ODDS_API_KEY')
    if not api_key:
        return "API key not found. Please set the environment variable 'THE_ODDS_API_KEY'."

    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {
        "apiKey": api_key,
        "bookmakers": "fanduel,pinnacle",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        # Write response to a JSON file for debugging
        with open('json/api_response.json', 'w') as f:
            json.dump(data, f, indent=4)
        return data
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code} - {response.text}")

def american_to_probability(american_odds):
    """Convert American odds to implied probability."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return -american_odds / (-american_odds + 100)

def format_american_odds(american_odds):
    """Format American odds to include a '+' sign for positive values."""
    if american_odds > 0:
        return f"+{american_odds}"
    return str(american_odds)

def format_point(point, market_type):
    """Format point values to include a '+' sign for positive values, except for totals."""
    try:
        point_val = float(point)
        if market_type != 'totals':
            if point_val > 0:
                return f"+{point}"
        return str(point)
    except ValueError:
        return point  # Return the point as is if it's not a number

def process_games(games):
    processed_games = []
    for game in games:
        if len(game['bookmakers']) > 0: # check if there are lines for the game. 
            game['commence_time'] = format_datetime(game['commence_time'])
            game['formatted_markets'] = []
            fanduel_markets = {market['key']: market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'fanduel' for market in bookmaker['markets']}
            pinnacle_markets = {market['key']: market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'pinnacle' for market in bookmaker['markets']}
            game['last_update'] = format_datetime(game['bookmakers'][0]['last_update'])
            for market_key in ['h2h', 'spreads', 'totals']:
                if market_key in fanduel_markets and market_key in pinnacle_markets:
                    formatted_market = {'type': market_key, 'data': []}
                    fanduel_data = fanduel_markets[market_key]
                    pinnacle_data = pinnacle_markets[market_key]
                    for f_outcome, p_outcome in zip(fanduel_data['outcomes'], pinnacle_data['outcomes']):
                        f_american = format_american_odds(f_outcome['price'])
                        p_american = format_american_odds(p_outcome['price'])
                        f_point = format_point(f_outcome.get('point', ''), market_key) if 'point' in f_outcome else ''
                        p_point = format_point(p_outcome.get('point', ''), market_key) if 'point' in p_outcome else ''


                        # Handle moneyline comparison
                        if market_key == 'h2h':
                            if int(f_american.replace('+', '')) > int(p_american.replace('+', '')):
                                formatted_market['data'].append({
                                    'name': f_outcome['name'],
                                    'fanduel': f_american,
                                    'pinnacle': p_american,
                                    'f_point': f_point,
                                    'p_point': p_point    
                                })
                        elif market_key == 'totals':
                            is_over = 'Over' in f_outcome['name']
                            if (is_over and float(f_point) < float(p_point)) or (not is_over and float(f_point) > float(p_point)):
                                formatted_market['data'].append({
                                    'name': f_outcome['name'],
                                    'fanduel': f_american,
                                    'pinnacle': p_american,
                                    'f_point': f_point,
                                    'p_point': p_point
                                })
                        elif market_key == 'spreads':
                            if (float(f_point) > float(p_point)):
                                formatted_market['data'].append({
                                    'name': f_outcome['name'],
                                    'fanduel': f_american,
                                    'pinnacle': p_american,
                                    'f_point': f_point,
                                    'p_point': p_point
                                })

                    if formatted_market['data']:
                        game['formatted_markets'].append(formatted_market)

            if game['formatted_markets']:
                processed_games.append(game)

    return processed_games





@app.route('/')
def home():
    sport_key = request.args.get('sport', 'baseball_mlb')
    games = fetch_odds(sport_key)
    processed_games = process_games(games)
    return render_template('odds.html', games=processed_games, sport=sport_key)

if __name__ == '__main__':
    app.run(debug=True)
