from app import app
from flask import render_template, request
from scripts.get_data import fetch_odds,process_games  # Import your function here

@app.route('/')
def home():
    sport_key = request.args.get('sport', 'baseball_mlb')
    games = fetch_odds(sport_key)
    processed_games = process_games(games)
    return render_template('odds.html', games=processed_games, sport=sport_key)
