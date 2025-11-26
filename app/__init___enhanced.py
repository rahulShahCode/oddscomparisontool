from flask import Flask, render_template, request, jsonify
from scripts.get_data_enhanced import fetch_odds, process_games
from scripts.risk_manager import RiskManager
from scripts.nfl_analyzer import NFLAnalyzer
import json
from datetime import datetime

app = Flask(__name__)

# Initialize components
risk_manager = RiskManager(bankroll=1000)  # Set your bankroll
nfl_analyzer = NFLAnalyzer()

def retrieve_data():
    """Fetch and process odds data for scheduled updates."""
    quota = 0
    sports = ['americanfootball_nfl', 'basketball_nba', 'basketball_ncaab']
    processed_sports = {}

    for sport in sports:
        try:
            curr_data, quota_last_used = fetch_odds(sport)
            quota += quota_last_used
            processed_games, quota_last_used = process_games(curr_data)
            quota += quota_last_used
            processed_sports[sport] = processed_games
        except Exception as e:
            print(f"Error fetching {sport}: {str(e)}")
            processed_sports[sport] = []

    processed_sports['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open('data/processed_games.json', 'w') as f:
        json.dump(processed_sports, f)

    print(f"Last used quota: {quota}")
    return processed_sports

@app.route('/')
def home():
    """Main route with sport selection."""
    sport_key = request.args.get('sport', 'americanfootball_nfl')  # Default to NFL

    try:
        games, _ = fetch_odds(sport_key)
        processed_games, _ = process_games(games)

        # Add risk management stats
        risk_stats = risk_manager.get_stats()

        return render_template('odds_enhanced.html',
                             games=processed_games,
                             sport=sport_key,
                             last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             risk_stats=risk_stats)
    except Exception as e:
        print(f"Error in home route: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/nfl-analysis')
def nfl_analysis():
    """Dedicated NFL analysis page with advanced metrics."""
    try:
        games, _ = fetch_odds('americanfootball_nfl')
        processed_games, _ = process_games(games)

        # Group games by confidence level
        high_confidence = []
        medium_confidence = []

        for game in processed_games:
            for market in game.get('formatted_markets', []):
                for outcome in market.get('data', []):
                    if outcome.get('confidence', 0) >= 70:
                        high_confidence.append({
                            'game': game,
                            'market': market,
                            'outcome': outcome
                        })
                    elif outcome.get('confidence', 0) >= 50:
                        medium_confidence.append({
                            'game': game,
                            'market': market,
                            'outcome': outcome
                        })

        return render_template('nfl_analysis.html',
                             high_confidence=high_confidence,
                             medium_confidence=medium_confidence,
                             last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        print(f"Error in NFL analysis: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/api/risk-stats')
def risk_stats():
    """API endpoint for risk management statistics."""
    return jsonify(risk_manager.get_stats())

@app.route('/api/log-result', methods=['POST'])
def log_result():
    """Log betting result for tracking."""
    data = request.json
    profit = data.get('profit', 0)
    risk_manager.log_result(profit)
    return jsonify({'success': True, 'new_stats': risk_manager.get_stats()})

# Setup scheduler for automatic updates (optional)
# scheduler = BackgroundScheduler()
# scheduler.add_job(func=retrieve_data, trigger="interval", minutes=15)
# scheduler.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)