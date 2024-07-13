import sqlite3
import json 
from scripts.get_data import fetch_odds,process_games 

sports = ['baseball_mlb','basketball_wnba', 'americanfootball_cfl', 'tennis_atp_wimbledon']

def store_data(curr_data): 
    pass 

def send_to_discord():
    pass 

def main(): 
    processed_sports = {}
    all_data = {} 
    for sport in sports:
        curr_data = fetch_odds(sport)
        processed_games = process_games(curr_data)
        processed_sports[sport] = processed_games
    with open('data/processed_games.json', 'w') as f:
        json.dump(processed_sports,f)
    with open('data/curr_data.json', 'w') as f : 
        json.dump(all_data, f)

def check_trend(): 
    pass 


if __name__ == '__main__':
    main() 