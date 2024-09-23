import requests 
from datetime import datetime
import pytz
import os 
import pandas as pd 
import sqlite3
from datetime import datetime 
import pytz 
my_bookmakers = ['fanduel', 'draftkings','espnbet','williamhill_us','pinnacle']
ATD_DELTA = 2.5
api_key = os.getenv('THE_ODDS_API_KEY')
sports = ['americanfootball_nfl']
markets = ['player_anytime_td','player_pass_tds', 'player_pass_yds', 'player_pass_completions', 'player_pass_attempts', 'player_pass_interceptions', 
           'player_rush_yds', 'player_rush_attempts', 'player_receptions', 'player_reception_yds']

def remove_commenced_games(): 
    conn = sqlite3.connect('odds.db')
    c = conn.cursor()
    
    # Get current time in EST/EDT
    current_time = datetime.now(pytz.timezone('US/Eastern'))
    
    # Remove games that have already commenced
    c.execute('DELETE FROM player_props WHERE event_commence_time < ?', (current_time,))
    
    conn.commit()
    conn.close() 

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
def find_favorable_lines(props, event_name : str, commence_time : str):
    results_with_different_points = []
    results_with_same_points = []
    bookmakers = props['bookmakers']
    pinnacle_data = next((b for b in bookmakers if b['key'] == 'pinnacle'), None)
    
    if not pinnacle_data:
        return None 
    
    for bookmaker in bookmakers:
        if bookmaker['key'] == 'pinnacle':
            continue  # Skip Pinny 

        for market in bookmaker['markets']:
            pinnacle_market = next((m for m in pinnacle_data['markets'] if m['key'] == market['key']), None)
            if not pinnacle_market:
                continue  # Pinny lines don't exist

            bet_type = transform_string(market['key'])  

            for outcome in market['outcomes']:
                pin_outcome = next((o for o in pinnacle_market['outcomes']
                                    if o['description'] == outcome['description'] and o['name'] == outcome['name']), None)
                if not pin_outcome:
                    continue  

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
                    "commence_time" : commence_time,
                    "event_name" : event_name,
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
                if not has_point_val and prob_delta >= ATD_DELTA and pin_outcome['price'] <=300: 
                    results_with_same_points.append(result_entry)
                elif has_point_val and ((outcome['name'] == "Over" and outcome['point'] < pin_outcome['point']) or \
                   (outcome['name'] == "Under" and outcome['point'] > pin_outcome['point'])) and \
                    pin_prob >= .5 and (point_delta >= 1 or prob_delta >= 2):
                    results_with_different_points.append(result_entry)
                elif has_point_val and outcome['point'] == pin_outcome['point'] and prob_delta > 5:
                    results_with_same_points.append(result_entry)

    # Sort results by most favorable probability difference and then by point value criteria
    results_with_different_points.sort(key=lambda x: x['delta'], reverse=True)
    results_with_same_points.sort(key=lambda x: x['delta'], reverse=True)

    return [results_with_different_points, results_with_same_points]

def output_to_html(diff_pts : list, same_pts : list):
    df_diff_pts = pd.DataFrame(diff_pts)
    df_same_pts = pd.DataFrame(same_pts)
    col_names = {
        'commence_time' : 'Start Time', 
        'event_name' : 'Event',
        'source' : 'Book',
        'player' : 'Player',
        'type' : 'Outcome',
        'point' : 'Point',
        'bet_type' : 'Prop',
        'odds' : 'Odds',
        'pinnacle' : 'Pinnacle Odds',
        'delta' : 'Odds % Delta',
        'point_delta' : 'Point Delta'
    }
    # Data Cleaning 
    if not df_diff_pts.empty:
        df_diff_pts = df_diff_pts.rename(columns=col_names)
        df_diff_pts = df_diff_pts[list(col_names.values())]
        df_diff_pts['Start Time'] = pd.to_datetime(df_diff_pts['Start Time'])
        df_diff_pts['Odds % Delta'] = df_diff_pts['Odds % Delta'].apply(lambda x: f"{round(x, 2)}%")



    if not df_same_pts.empty:
        df_same_pts = df_same_pts.rename(columns=col_names)
        # Ensure all columns in col_names.values() exist in the dataframe
        for col in col_names.values():
            if col not in df_same_pts.columns:
                df_same_pts[col] = None  # or a default value like 0 or np.nan
        df_same_pts = df_same_pts[list(col_names.values())]
        df_same_pts = df_same_pts.drop(columns=['Point Delta'], errors='ignore')
        df_same_pts['Start Time'] = pd.to_datetime(df_same_pts['Start Time'])
        df_same_pts['Odds % Delta'] = df_same_pts['Odds % Delta'].apply(lambda x: f"{round(x, 2)}%")

    diff_pts_html = df_diff_pts.to_html(index=False,classes='table table-striped table-bordered diff-pts-table')
    same_pts_html = df_same_pts.to_html(index=False,classes='table table-striped table-bordered same-pts-table')

    bootstrap_css = """
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <script>
        $(document).ready(function() {
            if ($('.diff-pts-table thead tr th').length) {
                $('.diff-pts-table').DataTable();
            }
            
            if ($('.same-pts-table thead tr th').length) {
                $('.same-pts-table').DataTable();
            }
        });
    </script>
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 20px;
        background-color: #f9f9f9;
    }
    h2 {
        color: #4A90E2;
        font-family: 'Trebuchet MS', sans-serif;
        text-align: center;
        font-size: 1.5em;
        margin-top: 20px;
    }
    .container {
        width: 80%;
        margin: auto;
        padding: 20px;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    }
    .table {
        margin: 20px 0;
        width: 100%;
    }
    </style>
    """

    html_content = f"""
    {bootstrap_css}
    <div class='container'>
        <h2>Diff Points</h2>
        {diff_pts_html}
        <h2>Same Points</h2>
        {same_pts_html}
    </div>
    """

    # Write HTML to a file
    with open("player_props_tables.html", "w") as file:
        file.write(html_content)

    print("HTML file with combined bets has been saved as 'player_props_tables.html'")


def store_props(props): 
    conn = sqlite3.connect('odds.db')
    c = conn.cursor()

    bookmakers = props['bookmakers']
    commence_time = convert_utc_to_edt(props['commence_time'])
    event_name = f"{props['away_team']} @ {props['home_team']}"
    sport_key = props['sport_key']
    event_id = props['id']

    markets = next((p['markets'] for p in bookmakers if p['key'] == 'pinnacle'), None) 
    if markets is not None: 
        for m in markets: 
            market_type = m['key']
            last_update = convert_utc_to_edt(m['last_update'])
            for o in m['outcomes']:
                player_name = o['description']
                outcome_type = o['name']
                odds = o['price']
                point_value = o.get('point', 0)
                c.execute('INSERT OR REPLACE INTO player_props VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                        (event_id,event_name,sport_key,market_type,outcome_type,player_name,point_value, odds, commence_time,last_update))
        conn.commit()
        conn.close()                             

def main(): 
    # TODO : Routine collection of player props. Check rate limits + gauge cost 
    # ~ >= TWice per day 
    sport = sports[0]
    events = get_events(sport)
    diff_pts = [] 
    same_pts = []
    for event in events: 
        props = fetch_props(event['id'], event['sport_key'])
        store_props(props)
        remove_commenced_games()
        event_name = f"{event['away_team']} @ {event['home_team']}"
        results = find_favorable_lines(props, event_name, event['commence_time_edt'])  # Process the data
        if results and results[0]:
            diff_pts.extend(results[0])
        if results and results[1]:
            same_pts.extend(results[1])
        # first_iteration = True 
        # if results is not None and (len(results[0]) != 0 or len(results[1]) != 0):
        #     print('{} @ {}'.format(props['away_team'], props['home_team']))
            # for result in results: 
            #     if first_iteration: 
            #         first_iteration = False 
            #         if len(result) != 0:
            #             print("\tResults with Different Point Values:")
            #             for r in result:
            #                 # Conditionally include 'point' in the print statement
            #                 point_info = f" {r['point']}" if 'point' in r and r['point'] is not None else ""
            #                 print(f"\t\t[{r['source']}] : {r['player']} [{r['type']}{point_info} {r['bet_type']}] @ {r['odds']}, Pinnacle {r['pinnacle']}\t {r.get('point_delta', '')} {r['delta']:.2f}%")
            #     else: 
            #         if len(result) != 0: 
            #             print("\tResults with Same Point Values:")
            #             for r in result:
            #                 # Conditionally include 'point' in the print statement
            #                 point_info = f" {r['point']}" if 'point' in r and r['point'] is not None else ""
            #                 print(f"\t\t[{r['source']}] : {r['player']} [{r['type']}{point_info} {r['bet_type']}] @ {r['odds']}, Pinnacle {r['pinnacle']} {r['delta']:.2f}%")
    output_to_html(diff_pts,same_pts)

main() 