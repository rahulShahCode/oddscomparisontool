from flask import Flask, render_template, request
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
    if response.status_code != 200:
        return f"Failed to retrieve data: {response.status_code} - {response.text}"
    
    return response.json()

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

def format_point(point):
    """Format point values to include a '+' sign for positive values."""
    try:
        if float(point) > 0:
            return f"+{point}"
        return str(point)
    except ValueError:
        return point  # Return the point as is if it's not a number

def process_games(games):
    processed_games = []
    for game in games:
        game['commence_time'] = format_datetime(game['commence_time'])
        game['formatted_markets'] = []
        fanduel_markets = {market['key']: market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'fanduel' for market in bookmaker['markets']}
        pinnacle_markets = {market['key']: market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'pinnacle' for market in bookmaker['markets']}
        
        for market_key in ['h2h', 'spreads', 'totals']:
            if market_key in fanduel_markets and market_key in pinnacle_markets:
                formatted_market = {'type': market_key, 'data': []}
                fanduel_data = fanduel_markets[market_key]
                pinnacle_data = pinnacle_markets[market_key]
                for f_outcome, p_outcome in zip(fanduel_data['outcomes'], pinnacle_data['outcomes']):
                    f_american = format_american_odds(f_outcome['price'])
                    p_american = format_american_odds(p_outcome['price'])
                    f_point = format_point(f_outcome.get('point', ''))
                    p_point = format_point(p_outcome.get('point', ''))

                    f_prob = american_to_probability(int(f_american.replace('+', '')))
                    p_prob = american_to_probability(int(p_american.replace('+', '')))
                    
                    # Checking point value favorability
                    if market_key in ['spreads', 'totals']:
                        f_point_val = float(f_point.replace('+', ''))
                        p_point_val = float(p_point.replace('+', ''))
                        if (f_point_val > p_point_val and f_point_val > 0) or \
                           (f_point_val < p_point_val and f_point_val < 0):
                                formatted_market['data'].append({
                                    'name': f_outcome['name'],
                                    'fanduel': f_american,
                                    'pinnacle': p_american,
                                    'f_point': f_point,
                                    'p_point': p_point
                                })
                    else:
                        if p_prob > f_prob:
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
