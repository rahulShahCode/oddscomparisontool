import requests
import json
import os
from datetime import datetime, timezone, timedelta
import logging
import time
import pytz
from scripts.nfl_analyzer import NFLAnalyzer
from scripts.risk_manager import RiskManager
from scripts.sharp_books_config import SHARP_SPORTSBOOKS, get_sharp_consensus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sportsbook configurations
RECREATIONAL_BOOKS = ['fanduel', 'draftkings', 'espnbet', 'williamhill_us', 'betmgm', 'betrivers', 'caesars']
SHARP_BOOKS = ['pinnacle', 'lowvig', 'bookmaker', 'betonline']
ALL_BOOKS = RECREATIONAL_BOOKS + SHARP_BOOKS

class EnhancedOddsProcessor:
    def __init__(self, bankroll=1000):
        self.request_counter = 0
        self.nfl_analyzer = NFLAnalyzer()
        self.risk_manager = RiskManager(bankroll)

    def american_to_probability(self, american_odds):
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return (100 / (american_odds + 100)) * 100
        else:
            return (-american_odds / (-american_odds + 100)) * 100

    def format_american_odds(self, american_odds):
        """Format American odds to include a '+' sign for positive values."""
        if american_odds > 0:
            return f"+{american_odds}"
        return str(american_odds)

    def format_point(self, point, market_type):
        """Format point values to include a '+' sign for positive values, except for totals."""
        try:
            point_val = float(point)
            if market_type != 'totals':
                if point_val > 0:
                    return f"+{point}"
            return str(point)
        except (ValueError, TypeError):
            return point or ''

    def format_datetime(self, timestamp):
        """Convert UTC timestamp to Eastern Time."""
        utc_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
        utc_zone = pytz.utc
        eastern_zone = pytz.timezone('America/New_York')
        utc_time = utc_zone.localize(utc_time)
        est_time = utc_time.astimezone(eastern_zone)
        return est_time.strftime('%B %d, %Y %H:%M')

    def get_sharp_consensus_for_outcome(self, game, market_type, outcome_name, point=None):
        """Get consensus from sharp books for a specific outcome."""
        sharp_data = {}

        for bookmaker in game.get('bookmakers', []):
            if bookmaker['key'] in SHARP_BOOKS:
                for market in bookmaker.get('markets', []):
                    if market['key'] == market_type:
                        sharp_data[bookmaker['key']] = market
                        break

        if game.get('sport_key', '').startswith('americanfootball_nfl'):
            return self.nfl_analyzer.calculate_sharp_consensus(
                sharp_data, market_type, outcome_name, point
            )
        else:
            # Generic sharp consensus for other sports
            odds_list = []
            for book, market in sharp_data.items():
                for outcome in market.get('outcomes', []):
                    if outcome['name'] == outcome_name:
                        if point is None or outcome.get('point') == point:
                            odds_list.append(outcome['price'])

            if len(odds_list) >= 2:
                avg_odds = sum(odds_list) / len(odds_list)
                return {
                    'has_consensus': True,
                    'consensus_line': avg_odds,
                    'confidence': min(len(odds_list) * 25, 100),
                    'books_agreeing': len(odds_list)
                }

            return {'has_consensus': False, 'consensus_line': None, 'confidence': 0}

    def find_best_recreational_odds(self, game, market_type):
        """Find the best odds from recreational books for each outcome."""
        rec_book_odds = {}

        for bookmaker in game.get('bookmakers', []):
            if bookmaker['key'] in RECREATIONAL_BOOKS:
                for market in bookmaker.get('markets', []):
                    if market['key'] == market_type:
                        rec_book_odds[bookmaker['key']] = {
                            'market': market,
                            'book': bookmaker['key']
                        }

        if not rec_book_odds:
            return []

        # Find best odds for each outcome
        best_odds = {}
        for book, data in rec_book_odds.items():
            for outcome in data['market'].get('outcomes', []):
                key = f"{outcome['name']}_{outcome.get('point', '')}"

                if key not in best_odds or outcome['price'] > best_odds[key]['price']:
                    best_odds[key] = {
                        'name': outcome['name'],
                        'price': outcome['price'],
                        'point': outcome.get('point'),
                        'bookmaker': book,
                        'link': outcome.get('link')
                    }

        return list(best_odds.values())

    def process_nfl_game(self, game):
        """Special processing for NFL games with key numbers and sharp consensus."""
        processed_markets = []

        for market_type in ['h2h', 'spreads', 'totals']:
            # Get best recreational odds
            best_rec_odds = self.find_best_recreational_odds(game, market_type)

            if not best_rec_odds:
                continue

            market_data = []

            for rec_outcome in best_rec_odds:
                # Get sharp consensus
                sharp_consensus = self.get_sharp_consensus_for_outcome(
                    game, market_type, rec_outcome['name'], rec_outcome.get('point')
                )

                if not sharp_consensus['has_consensus']:
                    continue

                # Calculate edge
                rec_prob = self.american_to_probability(rec_outcome['price'])
                sharp_prob = self.american_to_probability(sharp_consensus['consensus_line'])
                edge = sharp_prob - rec_prob

                # For NFL, add key number value
                key_value = 0
                if market_type in ['spreads', 'totals'] and rec_outcome.get('point'):
                    key_value = self.nfl_analyzer.calculate_key_number_value(
                        float(rec_outcome['point']), market_type
                    )

                adjusted_edge = edge + (key_value * 0.1)

                # Get minimum edge requirement
                game_situation = {
                    'spots': self.nfl_analyzer.check_situational_spot(game),
                    'key_number_value': key_value
                }
                min_edge = self.nfl_analyzer.get_nfl_edge_requirement(market_type, game_situation)

                # Check if bet qualifies
                if adjusted_edge >= min_edge:
                    # Risk management check
                    bet_info = {
                        'sport': game['sport_key'],
                        'edge': adjusted_edge,
                        'my_odds': rec_outcome['price'],
                        'pinnacle_odds': sharp_consensus['consensus_line'],
                        'market_type': market_type
                    }

                    should_bet, reason, stake_pct = self.risk_manager.should_place_bet(bet_info)

                    if should_bet:
                        market_data.append({
                            'name': rec_outcome['name'],
                            'rec_book': self.format_american_odds(rec_outcome['price']),
                            'sharp_consensus': self.format_american_odds(int(sharp_consensus['consensus_line'])),
                            'point': self.format_point(rec_outcome.get('point'), market_type),
                            'book_name': rec_outcome['bookmaker'],
                            'edge': round(edge, 2),
                            'key_value': round(key_value, 2),
                            'adjusted_edge': round(adjusted_edge, 2),
                            'sharp_books_agree': sharp_consensus['books_agreeing'],
                            'confidence': round(sharp_consensus['confidence'], 1),
                            'stake_pct': round(stake_pct * 100, 2),
                            'link': rec_outcome.get('link'),
                            'situational_notes': game_situation.get('spots', [])
                        })

            if market_data:
                processed_markets.append({
                    'type': market_type,
                    'data': market_data
                })

        return processed_markets

    def process_other_sports_game(self, game):
        """Process non-NFL games with standard sharp line comparison."""
        processed_markets = []

        # Get sport-specific minimum edge
        sport = game.get('sport_key', '')
        min_edge = self.risk_manager.get_min_edge_for_sport(sport)

        for market_type in ['h2h', 'spreads', 'totals']:
            best_rec_odds = self.find_best_recreational_odds(game, market_type)

            if not best_rec_odds:
                continue

            # Get Pinnacle odds for comparison
            pinnacle_market = None
            for bookmaker in game.get('bookmakers', []):
                if bookmaker['key'] == 'pinnacle':
                    for market in bookmaker.get('markets', []):
                        if market['key'] == market_type:
                            pinnacle_market = market
                            break
                    break

            if not pinnacle_market:
                continue

            market_data = []

            for rec_outcome in best_rec_odds:
                # Find matching Pinnacle outcome
                pinnacle_outcome = None
                for p_outcome in pinnacle_market.get('outcomes', []):
                    if p_outcome['name'] == rec_outcome['name']:
                        if rec_outcome.get('point') is None or p_outcome.get('point') == rec_outcome.get('point'):
                            pinnacle_outcome = p_outcome
                            break

                if not pinnacle_outcome:
                    continue

                # Calculate edge
                rec_prob = self.american_to_probability(rec_outcome['price'])
                pin_prob = self.american_to_probability(pinnacle_outcome['price'])
                edge = pin_prob - rec_prob

                if edge >= min_edge:
                    # Risk management check
                    bet_info = {
                        'sport': sport,
                        'edge': edge,
                        'my_odds': rec_outcome['price'],
                        'pinnacle_odds': pinnacle_outcome['price'],
                        'market_type': market_type
                    }

                    should_bet, reason, stake_pct = self.risk_manager.should_place_bet(bet_info)

                    if should_bet:
                        market_data.append({
                            'name': rec_outcome['name'],
                            'rec_book': self.format_american_odds(rec_outcome['price']),
                            'pinnacle': self.format_american_odds(pinnacle_outcome['price']),
                            'point': self.format_point(rec_outcome.get('point'), market_type),
                            'book_name': rec_outcome['bookmaker'],
                            'edge': round(edge, 2),
                            'stake_pct': round(stake_pct * 100, 2),
                            'link': rec_outcome.get('link')
                        })

            if market_data:
                processed_markets.append({
                    'type': market_type,
                    'data': market_data
                })

        return processed_markets

    def process_games(self, games):
        """Process games with enhanced NFL analysis and risk management."""
        processed_games = []
        quota_used = 0

        for game in games:
            # Skip games that have already started
            commence_time = datetime.fromisoformat(game['commence_time'][:-1]).replace(tzinfo=timezone.utc)
            if commence_time <= datetime.now(timezone.utc):
                continue

            game['commence_time'] = self.format_datetime(game['commence_time'])

            # Process based on sport
            if game.get('sport_key', '').startswith('americanfootball_nfl'):
                game['formatted_markets'] = self.process_nfl_game(game)
            else:
                game['formatted_markets'] = self.process_other_sports_game(game)

            if game['formatted_markets']:
                processed_games.append(game)

        return processed_games, quota_used

    def fetch_odds(self, sport_key):
        """Fetch odds from The Odds API."""
        api_key = os.getenv('THE_ODDS_API_KEY')
        if not api_key:
            raise ValueError("API key not found. Please set THE_ODDS_API_KEY environment variable.")

        url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
        params = {
            "apiKey": api_key,
            "bookmakers": ','.join(ALL_BOOKS),
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "includeLinks": "true"
        }

        # Rate limiting
        if self.request_counter >= 30:
            self.request_counter = 0
            time.sleep(1)

        response = requests.get(url, params=params)
        self.request_counter += 1

        quota_used = int(response.headers.get('x-requests-last', 0))

        if response.status_code == 200:
            games = response.json()

            # Filter out games that have already commenced
            current_time = datetime.now(timezone.utc)
            filtered_games = [
                game for game in games
                if datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%S%z") > current_time
            ]

            return filtered_games, quota_used
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code} - {response.text}")

# Create global instance
processor = EnhancedOddsProcessor()

# Export functions for compatibility
def fetch_odds(sport_key):
    return processor.fetch_odds(sport_key)

def process_games(games):
    return processor.process_games(games)