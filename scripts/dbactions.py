import sqlite3
from datetime import datetime
import pytz 

def to_est(dt_str):
    """Convert a UTC datetime string to EST/EDT timezone."""
    utc_time = datetime.strptime(dt_str[:-1], "%Y-%m-%dT%H:%M:%S") if dt_str.endswith('Z') else datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    est = pytz.timezone('US/Eastern')
    return utc_time.astimezone(est)

def store_odds(data):
    conn = sqlite3.connect('odds.db')
    c = conn.cursor()
    for game in data:
        commence_dttm = to_est(game['commence_time'])
        for bookmaker in game['bookmakers']:
            if bookmaker['key'] == 'pinnacle':
                for market in bookmaker['markets']:
                    for outcome in market['outcomes']:
                        last_updated_dttm = to_est(market['last_update'])  # Convert last_update to EST/EDT
                        point = outcome.get('point')
                        c.execute('INSERT OR REPLACE INTO pinnacle_lines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                                  (game['id'],f"{game['away_team']} @ {game['home_team']}" ,game['sport_key'], 
                                   market['key'], outcome['name'], point, outcome['price'],commence_dttm,last_updated_dttm))
                    
    conn.commit()
    conn.close()


def remove_commenced_games():
    conn = sqlite3.connect('odds.db')
    c = conn.cursor()
    
    # Get current time in EST/EDT
    current_time = datetime.now(pytz.timezone('US/Eastern'))
    
    # Remove games that have already commenced
    c.execute('DELETE FROM pinnacle_lines WHERE event_time < ?', (current_time,))
    
    conn.commit()
    conn.close()


def process_db(data):
    remove_commenced_games()
    store_odds(data)
    