"""
NFL-specific betting analyzer with key number analysis and sharp book consensus.
"""
import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

class NFLAnalyzer:
    """Specialized analyzer for NFL betting with key numbers and market dynamics."""

    def __init__(self):
        # NFL key numbers for spreads (margins of victory)
        self.key_spread_numbers = {
            3: 0.095,   # 9.5% of games land on 3
            7: 0.065,   # 6.5% of games land on 7
            10: 0.045,  # 4.5% of games land on 10
            6: 0.035,
            14: 0.030,
            4: 0.025,
            17: 0.020,
            21: 0.015
        }

        # Key totals
        self.key_total_numbers = {
            41: 0.040,
            44: 0.038,
            47: 0.035,
            40: 0.033,
            37: 0.030,
            43: 0.030,
            51: 0.028
        }

        # Teams that public loves to bet
        self.public_teams = [
            'Kansas City Chiefs', 'Buffalo Bills', 'Dallas Cowboys',
            'Green Bay Packers', 'San Francisco 49ers', 'Philadelphia Eagles'
        ]

        # Sharp books priority for NFL
        self.sharp_books_priority = [
            'pinnacle', 'circa', 'bookmaker', 'westgate', 'betonline', 'lowvig'
        ]

    def calculate_key_number_value(self, line: float, market_type: str) -> float:
        """
        Calculate additional value from being on the right side of key numbers.
        """
        if market_type == 'spreads':
            key_numbers = self.key_spread_numbers
        elif market_type == 'totals':
            key_numbers = self.key_total_numbers
        else:
            return 0

        value = 0
        for key_num, probability in key_numbers.items():
            # If we're getting points through a key number, that's valuable
            if market_type == 'spreads':
                if -key_num < line < -key_num + 0.5:
                    # We're getting points just past a key number (e.g., +3.5)
                    value += probability * 50  # Convert to percentage points
                elif key_num - 0.5 < line < key_num:
                    # We're laying points just before a key number (e.g., -2.5)
                    value += probability * 50

            elif market_type == 'totals':
                if abs(line - key_num) < 0.5:
                    # Being on either side of a key total
                    value += probability * 25

        return value

    def analyze_line_movement(self, opening_line: float, current_line: float,
                            opening_juice: int, current_juice: int) -> Dict:
        """Analyze line movement to detect sharp vs public money."""

        line_move = current_line - opening_line
        juice_move = current_juice - opening_juice

        analysis = {
            'line_movement': line_move,
            'juice_movement': juice_move,
            'interpretation': '',
            'sharp_side': None
        }

        # Reverse line movement (line moves opposite to juice)
        if line_move > 0 and juice_move < 0:
            analysis['interpretation'] = 'Reverse line movement - sharp money on underdog'
            analysis['sharp_side'] = 'underdog'
        elif line_move < 0 and juice_move > 0:
            analysis['interpretation'] = 'Reverse line movement - sharp money on favorite'
            analysis['sharp_side'] = 'favorite'

        # Steam move (rapid line movement)
        elif abs(line_move) >= 1.5:
            analysis['interpretation'] = f'Steam move {line_move:+.1f} points'
            analysis['sharp_side'] = 'favorite' if line_move < 0 else 'underdog'

        # Juice movement without line movement
        elif abs(juice_move) >= 15 and abs(line_move) < 0.5:
            analysis['interpretation'] = 'Sharp action via juice adjustment'
            analysis['sharp_side'] = 'favorite' if juice_move < 0 else 'underdog'

        return analysis

    def check_situational_spot(self, game: Dict) -> List[str]:
        """Identify situational advantages/disadvantages."""

        spots = []
        home_team = game.get('home_team', '')
        away_team = game.get('away_team', '')

        # Check for primetime games (more public action)
        game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
        if game_time.weekday() == 0:  # Monday
            spots.append('Monday Night Football - heavy public action')
        elif game_time.weekday() == 4 and game_time.hour >= 20:  # Thursday night
            spots.append('Thursday Night - short week, favor under')
        elif game_time.weekday() == 6 and game_time.hour >= 20:  # Sunday night
            spots.append('Sunday Night Football - heavy public action')

        # Check for public teams
        if home_team in self.public_teams:
            spots.append(f'Public team {home_team} at home - likely overvalued')
        if away_team in self.public_teams:
            spots.append(f'Public team {away_team} on road')

        # Divisional games tend to be lower scoring
        if self.is_divisional_game(home_team, away_team):
            spots.append('Divisional game - consider under')

        return spots

    def is_divisional_game(self, team1: str, team2: str) -> bool:
        """Check if teams are in the same division."""

        nfl_divisions = {
            'AFC East': ['Buffalo Bills', 'Miami Dolphins', 'New England Patriots', 'New York Jets'],
            'AFC North': ['Baltimore Ravens', 'Cincinnati Bengals', 'Cleveland Browns', 'Pittsburgh Steelers'],
            'AFC South': ['Houston Texans', 'Indianapolis Colts', 'Jacksonville Jaguars', 'Tennessee Titans'],
            'AFC West': ['Denver Broncos', 'Kansas City Chiefs', 'Las Vegas Raiders', 'Los Angeles Chargers'],
            'NFC East': ['Dallas Cowboys', 'New York Giants', 'Philadelphia Eagles', 'Washington Commanders'],
            'NFC North': ['Chicago Bears', 'Detroit Lions', 'Green Bay Packers', 'Minnesota Vikings'],
            'NFC South': ['Atlanta Falcons', 'Carolina Panthers', 'New Orleans Saints', 'Tampa Bay Buccaneers'],
            'NFC West': ['Arizona Cardinals', 'Los Angeles Rams', 'San Francisco 49ers', 'Seattle Seahawks']
        }

        for division, teams in nfl_divisions.items():
            if team1 in teams and team2 in teams:
                return True

        return False

    def calculate_sharp_consensus(self, books_data: Dict, market_type: str,
                                 outcome_name: str, point: Optional[float] = None) -> Dict:
        """Calculate consensus from sharp books with NFL-specific weighting."""

        sharp_odds = []
        sharp_books_found = []

        # Priority order for NFL sharp books
        for book_name in self.sharp_books_priority:
            if book_name in books_data:
                book_market = books_data[book_name]
                for outcome in book_market.get('outcomes', []):
                    if outcome['name'] == outcome_name:
                        if point is None or outcome.get('point') == point:
                            sharp_odds.append(outcome['price'])
                            sharp_books_found.append(book_name)
                            break

        if len(sharp_odds) < 2:
            return {
                'has_consensus': False,
                'consensus_line': None,
                'confidence': 0,
                'books_agreeing': 0
            }

        # Calculate weighted average with more weight to tier 1 books
        weights = [10 if book in ['pinnacle', 'circa', 'bookmaker'] else 7
                  for book in sharp_books_found]

        weighted_avg = sum(odds * weight for odds, weight in zip(sharp_odds, weights)) / sum(weights)

        # Calculate standard deviation for confidence
        std_dev = math.sqrt(sum((odds - weighted_avg) ** 2 for odds in sharp_odds) / len(sharp_odds))

        # Agreement score based on standard deviation
        agreement_score = max(0, 100 - std_dev)

        return {
            'has_consensus': True,
            'consensus_line': weighted_avg,
            'confidence': agreement_score,
            'books_agreeing': len(sharp_odds),
            'sharp_books': sharp_books_found,
            'std_deviation': std_dev
        }

    def get_nfl_edge_requirement(self, market_type: str, game_situation: Dict) -> float:
        """Get minimum edge requirement based on NFL-specific factors."""

        base_edge = 2.5  # Base NFL requirement

        # Adjust for market type
        if market_type == 'spreads':
            # Spreads are most efficient in NFL
            base_edge += 0.5
        elif market_type == 'totals':
            # Totals slightly less efficient
            base_edge += 0.25

        # Adjust for game situation
        if 'Monday Night' in game_situation.get('spots', []):
            # More public money, lines might be softer
            base_edge -= 0.25
        elif 'Divisional game' in game_situation.get('spots', []):
            # Divisional games are harder to predict
            base_edge += 0.5

        # Adjust for line value
        if game_situation.get('key_number_value', 0) > 2:
            # If we're getting significant key number value, reduce edge requirement
            base_edge -= 0.5

        return max(base_edge, 2.0)  # Never go below 2%

    def create_nfl_recommendation(self, game: Dict, market: Dict, outcome: Dict,
                                 sharp_consensus: Dict) -> Dict:
        """Create NFL-specific betting recommendation with all factors considered."""

        # Calculate key number value
        line = float(outcome.get('point', 0))
        key_value = self.calculate_key_number_value(line, market['type'])

        # Get situational factors
        situational_spots = self.check_situational_spot(game)

        # Calculate adjusted edge including key numbers
        raw_edge = outcome.get('edge', 0)
        adjusted_edge = raw_edge + (key_value * 0.1)  # Add 10% of key value to edge

        # Determine bet confidence
        confidence_factors = []
        confidence_score = 50  # Base confidence

        if sharp_consensus['has_consensus']:
            confidence_score += min(sharp_consensus['confidence'] * 0.3, 30)
            confidence_factors.append(f"{sharp_consensus['books_agreeing']} sharp books agree")

        if key_value > 3:
            confidence_score += 15
            confidence_factors.append(f"Strong key number value: {key_value:.1f}%")

        if adjusted_edge > 4:
            confidence_score += 10
            confidence_factors.append(f"Strong edge: {adjusted_edge:.1f}%")

        # Reduce confidence for certain situations
        if 'Public team' in ' '.join(situational_spots):
            confidence_score -= 10
            confidence_factors.append("Betting against public team (risky)")

        return {
            'sport': 'NFL',
            'game': f"{game['away_team']} @ {game['home_team']}",
            'bet_type': market['type'],
            'selection': f"{outcome['name']} {outcome.get('point', '')}".strip(),
            'odds': outcome['price'],
            'bookmaker': outcome['bookmaker'],
            'raw_edge': raw_edge,
            'key_number_value': key_value,
            'adjusted_edge': adjusted_edge,
            'confidence': min(confidence_score, 100),
            'confidence_factors': confidence_factors,
            'situational_notes': situational_spots,
            'sharp_consensus': {
                'line': sharp_consensus.get('consensus_line'),
                'books': sharp_consensus.get('sharp_books', []),
                'agreement': sharp_consensus.get('confidence', 0)
            },
            'recommended': adjusted_edge >= 2.5 and confidence_score >= 60
        }