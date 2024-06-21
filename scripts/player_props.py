import requests 
import json 
from datetime import datetime
import pytz
import os 

api_key = os.getenv('THE_ODDS_API_KEY')
sports = ['baseball_mlb']

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
        "markets" : "player_points,player_threes,player_rebounds,player_assists",
        "oddsFormat" : "american",  
        "bookmakers" : "fanduel,draftkings,pinnacle"
    }
    return requests.get(url,params=params).json()

# Function that gets all upcoming events for the given sport
def get_events(sport): 
    params = {'apiKey' : api_key}
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/events'
    resp = requests.get(url, params=params).json()
    for game in resp: 
        game['commence_time'] = convert_utc_to_edt(game['commence_time'])
    return resp 

# Function to filter games that start today in EDT timezone 
def get_todays_events(events): 
    # Get today's date in EDT
    today = datetime.now(pytz.timezone('America/New_York')).date()
    
    # Filter games that start today
    today_events = []
    for game in events:
        # Strip the timezone part and parse the datetime string
        datetime_str = game['commence_time'][:-4]  # Removes the " EDT"
        game_date = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S').date()
        if game_date == today:
            today_events.append(game)
    return today_events

def american_to_implied(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def find_favorable_lines(props):
    results_with_different_points = []
    results_with_same_points = []
    bookmakers = props['bookmakers']
    pinnacle_data = next((b for b in bookmakers if b['key'] == 'pinnacle'), None)
    
    if not pinnacle_data:
        return "No Pinnacle data available."

    # Define a simple mapping from market keys to bet types
    bet_type_mapping = {
        'player_points': 'Points',
        'player_assists': 'Assists',
        'player_rebounds': 'Rebounds',
        'player_threes': 'Threes'
    }

    for bookmaker in bookmakers:
        if bookmaker['key'] == 'pinnacle':
            continue  # Skip Pinnacle for comparison purposes

        for market in bookmaker['markets']:
            pinnacle_market = next((m for m in pinnacle_data['markets'] if m['key'] == market['key']), None)
            if not pinnacle_market:
                continue  # No corresponding market in Pinnacle for comparison

            bet_type = bet_type_mapping.get(market['key'], 'Unknown')  # Get the human-readable bet type

            for outcome in market['outcomes']:
                pin_outcome = next((o for o in pinnacle_market['outcomes']
                                    if o['description'] == outcome['description'] and o['name'] == outcome['name']), None)
                if not pin_outcome:
                    continue  # No corresponding outcome in Pinnacle for comparison

                # Calculate implied probabilities
                pin_prob = american_to_implied(pin_outcome['price'])
                other_prob = american_to_implied(outcome['price'])
                prob_delta = (pin_prob - other_prob) * 100

                # Prepare result entry
                result_entry = {
                    "source": bookmaker['title'],
                    "player": outcome['description'],
                    "type": outcome['name'],
                    "point": outcome['point'],
                    "bet_type": bet_type,
                    "odds": outcome['price'],
                    "pinnacle": f"{pin_outcome['description']} {pin_outcome['name']} {pin_outcome['point']} @ {pin_outcome['price']}",
                    "delta": prob_delta
                }

                # Determine if the line is more favorable
                if ((outcome['name'] == "Over" and outcome['point'] < pin_outcome['point']) or \
                   (outcome['name'] == "Under" and outcome['point'] > pin_outcome['point'])) and \
                    pin_prob >= .5:
                    results_with_different_points.append(result_entry)
                elif outcome['point'] == pin_outcome['point'] and prob_delta > 5:
                    results_with_same_points.append(result_entry)

    # Sort results by most favorable probability difference and then by point value criteria
    results_with_different_points.sort(key=lambda x: abs(x['delta']), reverse=True)
    results_with_same_points.sort(key=lambda x: abs(x['delta']), reverse=True)

    # Output results
    print("Results with Different Point Values:")
    for result in results_with_different_points:
        print(f"[{result['source']}] : {result['player']} [{result['type']} {result['point']} {result['bet_type']}] @ {result['odds']}, Pinnacle {result['pinnacle']} {result['delta']:.2f}%")

    print("\nResults with Same Point Values, Comparing Odds:")
    for result in results_with_same_points:
        print(f"[{result['source']}] : {result['player']} [{result['type']} {result['point']} {result['bet_type']}] @ {result['odds']}, Pinnacle {result['pinnacle']} {result['delta']:.2f}%")






def main(): 
    sport = sports[0]
    events = get_events(sport)
    today_events = get_todays_events(events)
    with open('json/events.json', 'w') as f:
        json.dump(events, f)
    for event in today_events: 
        props = fetch_props(event['id'], event['sport_key'])
        with open('json/player_props.json', 'w') as f:
            json.dump(props, f)
        find_favorable_lines(props)  # Process the data




main() 