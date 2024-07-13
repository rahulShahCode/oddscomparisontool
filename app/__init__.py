from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from scripts.get_data import fetch_odds,process_games  # Import your function here
import json 

app = Flask(__name__)
# def retrieve_data(): 
#     sports = ['baseball_mlb']
#     processed_sports = {}
#     all_data = {} 
#     for sport in sports:
#         curr_data = fetch_odds(sport)
#         data = curr_data 
#         processed_games = process_games(curr_data)
#         processed_sports[sport] = processed_games
#     with open('data/processed_games.json', 'w') as f:
#         json.dump(processed_sports,f)
#     with open('data/curr_data.json', 'w') as f : 
#         json.dump(all_data, f)

@app.route('/write_dict')
def write_dict(): 
    return jsonify(fetch_odds('baseball_mlb')), 200 
# @app.route('/')
# def home():
#     sport_key = request.args.get('sport', 'baseball_mlb')
#     with open('data/processed_games.json', 'r') as f: 
#         data = json.load(f)
#     if sport_key in data: 
#         print("Loading from file")
#         processed_games = data[sport_key]
#     else: 
#         games = fetch_odds(sport_key)
#         processed_games = process_games(games)
#         print("Fetched odds")
#     return render_template('odds.html', games=processed_games, sport=sport_key)


# #Initial run
# retrieve_data()

# # Setup scheduler
# scheduler = BackgroundScheduler()
# scheduler.add_job(func=retrieve_data, trigger="interval", minutes=30)
# scheduler.start()
