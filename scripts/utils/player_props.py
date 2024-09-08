import requests 
import json 
from datetime import datetime
import pytz
import os 

my_bookmakers = ['fanduel', 'draftkings','betmgm','williamhill_us','pinnacle']

api_key = os.getenv('THE_ODDS_API_KEY')
sports = ['americanfootball_nfl']
markets = ['player_anytime_td','player_pass_tds', 'player_pass_yds', 'player_pass_completions', 'player_pass_attempts', 'player_pass_interceptions', 'player_rush_yds', 'player_rush_attempts', 'player_receptions', 'player_reception_yds']
# Function to convert UTC to EDT 
def convert_utc_to_edt(utc_time_str):
    # Create a datetime object from the UTC time string
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    
    # Set the timezone to UTC
    utc_time = pytz.utc.localize(utc_time)
    
    # Convert to Eastern Daylight Time (EDT)
    edt_time = utc_time.astimezone(pytz.timezone('America/New_York'))
    
    return edt_time.strftime("%Y-%m-%d %H:%M:%S %Z")

# Function to fetch player props given the eventId
def fetch_props(eventId, sport): 
    url =  f"https://api.the-odds-api.com/v4/sports/{sport}/events/{eventId}/odds"
    params = {
        "apiKey" : api_key, 
        "regions" : "us",
        "markets" : ','.join(markets),
        "oddsFormat" : "american",  
        "bookmakers" : ','.join(my_bookmakers)
    }
    return requests.get(url,params=params).json()

# Function that gets all upcoming events for the given sport
def get_events(sport): 
    params = {'apiKey' : api_key}
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/events'
    resp = requests.get(url, params=params).json()
    for game in resp: 
        game['commence_time_edt'] = convert_utc_to_edt(game['commence_time'])[:-4]
    return resp 

# Function to filter games that start today in EDT timezone 
def get_todays_events(events): 
    # Get today's date in EDT
    eastern = pytz.timezone('America/New_York')
    # Filter games that start today
    today_events = []
    for game in events:
        # Parse the datetime string in EDT format
        game_time_edt = datetime.strptime(game['commence_time_edt'], '%Y-%m-%d %H:%M:%S')
        if eastern.localize(game_time_edt).date() == eastern.localize(datetime.now()).date() and eastern.localize(game_time_edt) > eastern.localize(datetime.now()):
            today_events.append(game)
    return today_events

def american_to_implied(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)
    
def transform_string(input_str):
    # Split the input string by underscores
    parts = input_str.split('_')
    
    # Remove the first word and capitalize the second word
    if len(parts) > 1:
        transformed_str = parts[1].capitalize()
    
    # Capitalize the remaining words and join them with spaces
    if len(parts) > 2:
        transformed_str += ' ' + ' '.join([word.capitalize() for word in parts[2:]])
    
    return transformed_str
def find_favorable_lines(props):
    results_with_different_points = []
    results_with_same_points = []
    bookmakers = props['bookmakers']
    pinnacle_data = next((b for b in bookmakers if b['key'] == 'pinnacle'), None)
    
    if not pinnacle_data:
        return None 



    for bookmaker in bookmakers:
        if bookmaker['key'] == 'pinnacle':
            continue  # Skip Pinnacle for comparison purposes

        for market in bookmaker['markets']:
            pinnacle_market = next((m for m in pinnacle_data['markets'] if m['key'] == market['key']), None)
            if not pinnacle_market:
                continue  # No corresponding market in Pinnacle for comparison

            bet_type = transform_string(market['key'])  # Get the human-readable bet type

            for outcome in market['outcomes']:
                pin_outcome = next((o for o in pinnacle_market['outcomes']
                                    if o['description'] == outcome['description'] and o['name'] == outcome['name']), None)
                if not pin_outcome:
                    continue  # No corresponding outcome in Pinnacle for comparison

                # Calculate implied probabilities
                pin_prob = american_to_implied(pin_outcome['price'])
                other_prob = american_to_implied(outcome['price'])
                prob_delta = (pin_prob - other_prob) * 100

                point_delta = None 
                has_point_val = 'point' in outcome 
                if outcome['name'] == 'Over' and has_point_val:
                    point_delta = pin_outcome['point'] - outcome['point']
                elif has_point_val: 
                    point_delta = outcome['point'] - pin_outcome['point']
                # Prepare result entry
                result_entry = {
                    "source": bookmaker['title'],
                    "player": outcome['description'],
                    "type": outcome['name'],
                    "bet_type": bet_type,
                    "odds": outcome['price'],
                    "delta": prob_delta
                }

                if has_point_val:
                    result_entry['point'] = outcome['point']
                    result_entry['pinnacle'] = f"{pin_outcome['description']} {pin_outcome['name']} {pin_outcome['point']} @ {pin_outcome['price']}"
                else: 
                    result_entry['pinnacle'] = f"{pin_outcome['description']} {pin_outcome['name']} @ {pin_outcome['price']}"
                # Add point_delta only if it's not None
                if point_delta is not None:
                    result_entry["point_delta"] = point_delta

                # Determine if the line is more favorable
                if not has_point_val and prob_delta >= 5: 
                    results_with_same_points.append(result_entry)
                elif has_point_val and ((outcome['name'] == "Over" and outcome['point'] < pin_outcome['point']) or \
                   (outcome['name'] == "Under" and outcome['point'] > pin_outcome['point'])) and \
                    pin_prob >= .5 and (point_delta > 2 or prob_delta >= 1):
                    results_with_different_points.append(result_entry)
                elif has_point_val and outcome['point'] == pin_outcome['point'] and prob_delta > 5:
                    results_with_same_points.append(result_entry)

    # Sort results by most favorable probability difference and then by point value criteria
    results_with_different_points.sort(key=lambda x: x['delta'], reverse=True)
    results_with_same_points.sort(key=lambda x: x['delta'], reverse=True)

    return [results_with_different_points, results_with_same_points]



def main(): 
    sport = sports[0]
    events = get_events(sport)
    today_events = get_todays_events(events)
    with open('data/debug/events.json', 'w') as f:
        json.dump(events, f)
    for event in today_events: 
        props = fetch_props(event['id'], event['sport_key'])
        with open('data/debug/player_props.json', 'w') as f:
            json.dump(props, f)
        results = find_favorable_lines(props)  # Process the data
        first_iteration = True 
        if results is not None and (len(results[0]) != 0 or len(results[1]) != 0):
            print('{} @ {}'.format(props['away_team'], props['home_team']))
        for result in results: 
            if first_iteration: 
                first_iteration = False 
                if len(result) != 0:
                    print("\tResults with Different Point Values:")
                    for r in result:
                        # Conditionally include 'point' in the print statement
                        point_info = f" {r['point']}" if 'point' in r and r['point'] is not None else ""
                        print(f"\t\t[{r['source']}] : {r['player']} [{r['type']}{point_info} {r['bet_type']}] @ {r['odds']}, Pinnacle {r['pinnacle']}\t {r.get('point_delta', '')} {r['delta']:.2f}%")
            else: 
                if len(result) != 0: 
                    print("\tResults with Same Point Values:")
                    for r in result:
                        # Conditionally include 'point' in the print statement
                        point_info = f" {r['point']}" if 'point' in r and r['point'] is not None else ""
                        print(f"\t\t[{r['source']}] : {r['player']} [{r['type']}{point_info} {r['bet_type']}] @ {r['odds']}, Pinnacle {r['pinnacle']} {r['delta']:.2f}%")




main() 