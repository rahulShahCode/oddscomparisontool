import requests
import json
import os
from datetime import datetime, timezone, timedelta
import logging 
import time


my_bookmakers = ['fanduel', 'draftkings','espnbet','williamhill_us']
sharp_bookmakers = ['pinnacle', 'lowvig']
request_counter = 0

def get_best_odds(books): 
    market_type = list(books.values())[0]['key']
    outcomes = {} 
    for book, details in books.items(): 
        for outcome in details['outcomes']:
            name = outcome['name']
            price = outcome['price']
            point = outcome.get('point', None)
            if name not in outcomes:
                outcomes[name] = {
                    'best_price': price,
                    'best_point': point,
                    'sportsbook': book
                }
            else:
                current_best = outcomes[name]
                if market_type == 'h2h':
                    if price > current_best['best_price']:
                        outcomes[name] = {
                            'best_price': price,
                            'best_point': point,
                            'sportsbook': book
                        }
                elif market_type == 'totals':
                    if name == 'Over':
                        if point < current_best['best_point'] or (point == current_best['best_point'] and price > current_best['best_price']):
                            outcomes[name] = {
                                'best_price': price,
                                'best_point': point,
                                'sportsbook': book
                            }
                    elif name == 'Under':
                        if point > current_best['best_point'] or (point == current_best['best_point'] and price > current_best['best_price']):
                            outcomes[name] = {
                                'best_price': price,
                                'best_point': point,
                                'sportsbook': book
                            }
                elif market_type == 'spreads':
                    if abs(point) > abs(current_best['best_point']) or (abs(point) == abs(current_best['best_point']) and price > current_best['best_price']):
                        outcomes[name] = {
                            'best_price': price,
                            'best_point': point,
                            'sportsbook': book
                        }
    best_odds = []
    for name, details in outcomes.items():
        best_odds.append({
            'name': name,
            'price': details['best_price'],
            'point': details['best_point'],
            'sportsbook': details['sportsbook']
        })
    
    return best_odds

def beats_lowvig(lv_odds : dict, my_book_odds : dict, market_key : str):
    if market_key == 'h2h':
        pass 
    elif market_key == 'totals':
        pass 
    elif market_key == 'spreads': 
        pass 
def find_matching_outcome(outcomes, target): 
    for outcome in outcomes:
        if outcome['name'] == target['name'] and outcome['point'] == target['point']:
            return outcome
    return None

def check_alt_line(eventId,market_type,sport,my_outcome):
    global request_counter
    event_url = f'https://api.the-odds-api.com/v4/sports/{sport}/events/{eventId}/odds'
    params = {
        "apiKey" : os.getenv('THE_ODDS_API_KEY'),
        "bookmakers" : "pinnacle",
        "markets" : market_type,
        "oddsFormat" : "american"
    }
    if (request_counter >= 30):
        request_counter = 0
        time.sleep(1)
    response = requests.get(event_url,params=params)
    request_counter += 1 
    quota_used = int(response.headers._store.get('x-requests-last')[1])
    # Log the status code and response content
    logging.debug(f"Status Code: {response.status_code}")
    logging.debug(f"Response Content: {response.text}")
    logging.debug(f"Response JSON: {response.json()}")
    alt_lines = response.json()['bookmakers'][0]['markets'][0]['outcomes']
    matching_alt_line = find_matching_outcome(alt_lines,my_outcome)
    if matching_alt_line is not None: 
        my_prob = american_to_probability(int(my_outcome['price']))
        p_prob = american_to_probability(int(matching_alt_line['price']))
        if (p_prob - my_prob) >= 1:
            return matching_alt_line, quota_used 
    return None,quota_used
def match_market(market_lst,market_type): 
    for market in market_lst: 
        if market['key'] == market_type:
            return market  
    return None 

def get_markets_by_type(bookmakers, market_type):
    result = {}
    for bookmaker, market_lst in bookmakers.items():
        market = match_market(market_lst,market_type)
        if market: 
            result[bookmaker] = market 
    return result


def decimal_to_american(odds):
    if odds > 2.0:
        return f"+{int((odds - 1) * 100)}"
    elif odds == 2.0:
        return "+100"
    else:
        return str(int(-100 / (odds - 1)))

def format_datetime(timestamp):
    utc_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
    est_time = utc_time - timedelta(hours=4)  # Adjust for Eastern Standard Time
    return est_time.strftime('%B %d, %Y %H:%M')


def american_to_probability(american_odds):
    """Convert American odds to implied probability."""
    if american_odds > 0:
        return (100 / (american_odds + 100)) * 100
    else:
        return (-american_odds / (-american_odds + 100)) * 100
    
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
    quota_sum = 0 
    processed_games = []
    for game in games:
        commence_time = datetime.fromisoformat(game['commence_time'][:-1]).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)   
        if commence_time > now: 
            game['formatted_markets'] = []
            game['commence_time'] = format_datetime(game['commence_time'])
            my_book_markets = {
                book: [market for bookmaker in game['bookmakers'] if bookmaker['key'] == book for market in bookmaker['markets']]
                for book in my_bookmakers
            }
            pinnacle_markets = [market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'pinnacle' for market in bookmaker['markets']]
            lowvig_markets = [market for bookmaker in game['bookmakers'] if bookmaker['key'] == 'lowvig' for market in bookmaker['markets']]
            for market_key in ['h2h','spreads','totals']:
                books_for_curr_market = get_markets_by_type(my_book_markets, market_key)
                pinnacle_data = match_market(pinnacle_markets,market_key)
                lowvig_data = match_market(lowvig_markets,market_key)
                if books_for_curr_market and pinnacle_data:
                    formatted_market = {'type': market_key, 'data': []}
                    best_odds = get_best_odds(books_for_curr_market)

                    if lowvig_data: 
                        outcomes_iter =  zip(best_odds, pinnacle_data['outcomes'], lowvig_data['outcomes'])
                    else: 
                        outcomes_iter =  zip(best_odds, pinnacle_data['outcomes'])
                    for outcomes in outcomes_iter:
                        if lowvig_data: 
                            my_outcome, p_outcome, lv_outcome = outcomes
                            lv_point = format_point(lv_outcome.get('point', ''), market_key) if 'point' in lv_outcome else '' 
                            lv_american = format_american_odds(lv_outcome['price'])
                        else: 
                            my_outcome, p_outcome = outcomes
                            lv_point = ''
                            lv_american = ''
                        my_american = format_american_odds(my_outcome['price'])
                        p_american = format_american_odds(p_outcome['price'])
                        my_point = format_point(my_outcome['point'], market_key) if my_outcome['point'] is not None else ''
                        p_point = format_point(p_outcome.get('point', ''), market_key) if 'point' in p_outcome else ''

                        my_prob = american_to_probability(int(my_outcome['price'])) 
                        p_prob = american_to_probability(int(p_outcome['price']))
                        pct_edge = round(p_prob - my_prob,2) 
                        # Handle moneyline comparison
                        if market_key == 'h2h':
                            if pct_edge >= 1:
                                formatted_market['data'].append({
                                    'name': my_outcome['name'],
                                    'my_book': my_american,
                                    'pinnacle': p_american,
                                    'my_point': my_point,
                                    'p_point': p_point,
                                    'book_name' : my_outcome['sportsbook'],
                                    'pct_edge' : pct_edge,
                                    'lv_point' : lv_point,
                                    'lv_price' : lv_american,
                                })
                        elif market_key == 'totals':
                            is_over = 'Over' in my_outcome['name']
                            if (is_over and float(my_point) < float(p_point)) \
                            or (not is_over and float(my_point) > float(p_point)):
                                alt_line, quota_last_used = check_alt_line(game['id'],'alternate_'+market_key,game['sport_key'], my_outcome)
                                quota_sum += quota_last_used
                                if alt_line is not None:
                                    pct_edge = round(american_to_probability(int(alt_line['price'])) - my_prob,2)
                                    formatted_market['data'].append({
                                        'name': my_outcome['name'],
                                        'my_book': my_american,
                                        'pinnacle': alt_line['price'],
                                        'my_point': my_point,
                                        'p_point': alt_line['point'],
                                        'book_name' : my_outcome['sportsbook'],
                                        'pct_edge' : pct_edge,
                                        'lv_point' : lv_point,
                                        'lv_price' : lv_american,
                                    })
                            elif (float(my_point) == float(p_point) and pct_edge >= 1):
                                formatted_market['data'].append({
                                    'name': my_outcome['name'],
                                    'my_book': my_american,
                                    'pinnacle': p_american,
                                    'my_point': my_point,
                                    'p_point': p_point,
                                    'book_name' : my_outcome['sportsbook'],
                                    'pct_edge' : pct_edge,
                                    'lv_point' : lv_point,
                                    'lv_price' : lv_american,
                                })
                        elif market_key == 'spreads':
                            if (float(my_point) != float(p_point)):
                                alt_line, quota_last_used = check_alt_line(game['id'],'alternate_'+market_key,game['sport_key'], my_outcome)
                                quota_sum += quota_last_used
                                if alt_line is not None: 
                                    pct_edge = round(american_to_probability(int(alt_line['price'])) - my_prob,2)
                                    formatted_market['data'].append({
                                        'name': my_outcome['name'],
                                        'my_book': my_american,
                                        'pinnacle': alt_line['price'],
                                        'my_point': my_point,
                                        'p_point': alt_line['point'],
                                        'book_name' : my_outcome['sportsbook'],
                                        'pct_edge' : pct_edge,
                                        'lv_point' : lv_point,
                                        'lv_price' : lv_american,
                                    })
                            elif(float(my_point) == float(p_point) and pct_edge >= 1): 
                                formatted_market['data'].append({
                                    'name': my_outcome['name'],
                                    'my_book': my_american,
                                    'pinnacle': p_american,
                                    'my_point': my_point,
                                    'p_point': p_point,
                                    'book_name' : my_outcome['sportsbook'],
                                    'pct_edge' : pct_edge,
                                    'lv_point' : lv_point,
                                    'lv_price' : lv_american,
                                })

                    if formatted_market['data']:
                        game['formatted_markets'].append(formatted_market)

            if game['formatted_markets']:
                processed_games.append(game)

    return processed_games, quota_sum


def fetch_odds(sport_key):
    global request_counter
    api_key = os.getenv('THE_ODDS_API_KEY')
    if not api_key:
        return "API key not found. Please set the environment variable 'THE_ODDS_API_KEY'."

    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {
        "apiKey": api_key,
        "bookmakers": ','.join(my_bookmakers + sharp_bookmakers),
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    # sleep to avoid rate limiting
    if (request_counter >= 30):
        request_counter = 0
        time.sleep(1)
    response = requests.get(url, params=params)
    request_counter += 1 
    quota_used = int(response.headers._store.get('x-requests-last')[1])
    if response.status_code == 200:
        games = response.json()
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code} - {response.text}")
    
    # Filter out games that have already commenced using list comprehension
    current_time = datetime.now(timezone.utc)
    filtered_games = [game for game in games if datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%S%z") > current_time]
    return filtered_games, quota_used
