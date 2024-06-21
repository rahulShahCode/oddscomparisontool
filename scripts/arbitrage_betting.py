import requests
import json
import os
from datetime import datetime, timezone, timedelta

bookmakers = ['betmgm','draftkings','fanduel', 'williamhill_us','espnbet','fliff']
api_key = os.getenv('THE_ODDS_API_KEY')
events_data = {}

def fetch_odds(sport_key):
    if not api_key:
        return "API key not found. Please set the environment variable 'THE_ODDS_API_KEY'."

    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {
        "apiKey": api_key,
        "bookmakers": ','.join(bookmakers),
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        games = response.json()
        return games 
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code} - {response.text}")
def fetch_sports():
    if not api_key:
        return "API key not found. Please set the environment variable 'THE_ODDS_API_KEY'."    
    url = f'https://api.the-odds-api.com/v4/sports/?apiKey={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        filtered_sports = []  
        sports = response.json()
        for sport in sports: 
            if sport['active'] and not sport['has_outrights']:
                filtered_sports.append(sport['key'])
        return filtered_sports 
    
import json

def calculate_implied_probability(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)

def find_arbitrage_opportunities(data):
    arbitrage_opportunities = []

    for game in data:
        bookmakers = game.get('bookmakers', [])
        for market_type in ['h2h', 'spreads', 'totals']:
            market_outcomes = {}

            # Collect all outcomes from different bookmakers
            for bookmaker in bookmakers:
                for market in bookmaker.get('markets', []):
                    if market['key'] == market_type:
                        for outcome in market['outcomes']:
                            name = outcome['name']
                            price = outcome['price']
                            if name not in market_outcomes:
                                market_outcomes[name] = []
                            market_outcomes[name].append({
                                'bookmaker': bookmaker['key'],
                                'price': price,
                                'implied_prob': calculate_implied_probability(price)
                            })

            # Check for arbitrage opportunities
            for outcome1, outcome2 in zip(market_outcomes.values(), market_outcomes.values()):
                if len(outcome1) > 1 and len(outcome2) > 1 and outcome1 != outcome2:
                    best_odds_outcome1 = min(outcome1, key=lambda x: x['implied_prob'])
                    best_odds_outcome2 = min(outcome2, key=lambda x: x['implied_prob'])

                    total_implied_prob = best_odds_outcome1['implied_prob'] + best_odds_outcome2['implied_prob']
                    if total_implied_prob < 1:
                        arbitrage_opportunity = {
                            'game': f"{game['home_team']} vs {game['away_team']}",
                            'market': market_type,
                            'outcome1': {
                                'bookmaker': best_odds_outcome1['bookmaker'],
                                'price': best_odds_outcome1['price'],
                                'implied_prob': best_odds_outcome1['implied_prob']
                            },
                            'outcome2': {
                                'bookmaker': best_odds_outcome2['bookmaker'],
                                'price': best_odds_outcome2['price'],
                                'implied_prob': best_odds_outcome2['implied_prob']
                            },
                            'total_implied_prob': total_implied_prob,
                            'return': (1 / total_implied_prob - 1) * 100
                        }
                        arbitrage_opportunities.append(arbitrage_opportunity)

    # Sort by best return first
    arbitrage_opportunities.sort(key=lambda x: x['return'], reverse=True)
    return arbitrage_opportunities

sports = fetch_sports()
for sport_key in sports: 
    data = fetch_odds(sport_key)
    arbitrage_opportunities = find_arbitrage_opportunities(data)
    # Print the sorted list of arbitrage opportunities
    for opportunity in arbitrage_opportunities:
        print(f"Game: {opportunity['game']}, Market: {opportunity['market']}, Return: {opportunity['return']:.2f}%")
        print(f"  Outcome 1 - Bookmaker: {opportunity['outcome1']['bookmaker']}, Price: {opportunity['outcome1']['price']}, Implied Prob: {opportunity['outcome1']['implied_prob']:.4f}")
        print(f"  Outcome 2 - Bookmaker: {opportunity['outcome2']['bookmaker']}, Price: {opportunity['outcome2']['price']}, Implied Prob: {opportunity['outcome2']['implied_prob']:.4f}")
        print()





