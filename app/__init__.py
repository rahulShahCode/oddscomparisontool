from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from scripts.get_data import fetch_odds,process_games 
from scripts.dbactions import process_db
import json 
from datetime import datetime
app = Flask(__name__)
def retrieve_data(): 
    quota = 0
    sports = ['americanfootball_nfl']
    processed_sports = {}
    for sport in sports:
        curr_data, quota_last_used = fetch_odds(sport)
        quota += quota_last_used
        process_db(curr_data)
        processed_games, quota_last_used = process_games(curr_data)
        quota += quota_last_used
        processed_sports[sport] = processed_games     
        processed_sports['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('data/processed_games.json', 'w') as f:
        json.dump(processed_sports,f)
    print("Last used quota: " + str(quota))
@app.route('/')
def home():
    sport_key = request.args.get('sport', 'baseball_mlb')
    with open('data/processed_games.json', 'r') as f: 
        data = json.load(f)
    if sport_key in data: 
        print("Loading from file")
        processed_games = data[sport_key]
    else: 
        games = fetch_odds(sport_key)
        processed_games = process_games(games)
        print("Fetched odds")
    return render_template('odds.html', games=processed_games, sport=sport_key, last_updated=data['last_update'])


#Initial run
retrieve_data()

# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=retrieve_data, trigger="interval", minutes=20)
scheduler.start()
