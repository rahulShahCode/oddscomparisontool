"""
Enhanced odds processor with risk management and better edge validation.
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from scripts.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class EnhancedOddsProcessor:
    """Process odds with improved edge detection and risk management."""

    def __init__(self, bankroll: float = 1000.0):
        self.risk_manager = RiskManager(bankroll)
        self.sharp_books = ['pinnacle', 'lowvig', 'circa', 'bookmaker']
        self.recreational_books = ['fanduel', 'draftkings', 'betmgm', 'caesars', 'betrivers']

    def validate_edge(self, game: Dict, market: Dict, outcome: Dict) -> Dict:
        """
        Validate if an edge is real and worth betting.

        Returns dict with:
        - is_valid: bool
        - confidence: float (0-100)
        - warnings: List[str]
        - recommended_stake: float
        """
        warnings = []

        # Extract bet information
        sport = game.get('sport_key', '')
        my_odds = outcome.get('my_odds', 0)
        pinnacle_odds = outcome.get('pinnacle_odds', 0)
        edge = outcome.get('edge', 0)
        market_type = market.get('type', '')

        # Check game timing - avoid bets too close to game time
        commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
        time_until_game = (commence_time - datetime.now(timezone.utc)).total_seconds() / 3600

        if time_until_game < 0.5:  # Less than 30 minutes
            warnings.append("Game starting very soon - lines may be stale")
            confidence_penalty = 20
        elif time_until_game < 2:  # Less than 2 hours
            warnings.append("Close to game time - verify current lines")
            confidence_penalty = 10
        else:
            confidence_penalty = 0

        # Check line agreement across sharp books
        sharp_agreement = self.check_sharp_book_agreement(game, market, outcome)
        if sharp_agreement < 0.7:  # Less than 70% of sharp books agree
            warnings.append("Sharp books disagree on this line")
            confidence_penalty += 15

        # Sport-specific adjustments for NCAAF
        if sport == 'americanfootball_ncaaf':
            # College games have more variance
            warnings.append("NCAAF - high variance sport")
            confidence_penalty += 10

            # Check for rivalry games or unusual matchups
            if self.is_rivalry_game(game):
                warnings.append("Potential rivalry game - unpredictable")
                confidence_penalty += 15

        # Calculate confidence score
        base_confidence = min(edge * 10, 100)  # Edge of 10% = 100% confidence
        final_confidence = max(base_confidence - confidence_penalty, 0)

        # Get risk manager recommendation
        bet_info = {
            'sport': sport,
            'edge': edge,
            'my_odds': my_odds,
            'pinnacle_odds': pinnacle_odds,
            'market_type': market_type
        }

        should_bet, reason, stake_pct = self.risk_manager.should_place_bet(bet_info)

        # Additional validation
        if final_confidence < 50:
            should_bet = False
            reason = "Confidence too low (<50%)"

        return {
            'is_valid': should_bet,
            'confidence': final_confidence,
            'warnings': warnings,
            'recommended_stake_pct': stake_pct * 100 if should_bet else 0,
            'reason': reason,
            'time_to_game_hours': time_until_game
        }

    def check_sharp_book_agreement(self, game: Dict, market: Dict, outcome: Dict) -> float:
        """
        Check how many sharp books agree with Pinnacle's line.
        Returns percentage of agreement (0-1).
        """
        sharp_odds = []
        target_point = outcome.get('point')

        for bookmaker in game.get('bookmakers', []):
            if bookmaker['key'] in self.sharp_books:
                book_markets = bookmaker.get('markets', [])
                for book_market in book_markets:
                    if book_market['key'] == market['type']:
                        for book_outcome in book_market.get('outcomes', []):
                            if book_outcome['name'] == outcome['name']:
                                if target_point is None or book_outcome.get('point') == target_point:
                                    sharp_odds.append(book_outcome['price'])

        if len(sharp_odds) < 2:
            return 0.5  # Not enough data

        # Check if odds are within reasonable range (within 20 cents)
        pinnacle_price = outcome['pinnacle_odds']
        agreements = sum(1 for odds in sharp_odds if abs(odds - pinnacle_price) <= 20)

        return agreements / len(sharp_odds)

    def is_rivalry_game(self, game: Dict) -> bool:
        """
        Detect if this might be a rivalry game based on team names.
        This is a simple heuristic - could be enhanced with a rivalry database.
        """
        # Common rivalry keywords
        rivalry_indicators = [
            ('Ohio State', 'Michigan'),
            ('Alabama', 'Auburn'),
            ('Texas', 'Oklahoma'),
            ('Florida', 'Georgia'),
            ('USC', 'UCLA'),
            # Add more rivalries
        ]

        home_team = game.get('home_team', '').lower()
        away_team = game.get('away_team', '').lower()

        for team1, team2 in rivalry_indicators:
            if (team1.lower() in home_team and team2.lower() in away_team) or \
               (team2.lower() in home_team and team1.lower() in away_team):
                return True

        return False

    def create_bet_recommendation(self, game: Dict, market: Dict, outcome: Dict,
                                 validation: Dict) -> Dict:
        """Create a detailed betting recommendation."""

        # Calculate potential profit
        my_odds = outcome.get('my_odds', 0)
        stake_pct = validation['recommended_stake_pct'] / 100
        stake = self.risk_manager.bankroll * stake_pct

        if my_odds > 0:
            potential_profit = stake * (my_odds / 100)
        else:
            potential_profit = stake * (100 / abs(my_odds))

        return {
            'game': f"{game.get('away_team')} @ {game.get('home_team')}",
            'sport': game.get('sport_key'),
            'market': market.get('type'),
            'bet': f"{outcome.get('name')} {outcome.get('point', '')}".strip(),
            'odds': my_odds,
            'bookmaker': outcome.get('bookmaker'),
            'edge': outcome.get('edge'),
            'confidence': validation['confidence'],
            'recommended_stake': round(stake, 2),
            'stake_percentage': round(stake_pct * 100, 2),
            'potential_profit': round(potential_profit, 2),
            'warnings': validation['warnings'],
            'time_to_game': f"{validation['time_to_game_hours']:.1f} hours",
            'should_bet': validation['is_valid'],
            'reason': validation['reason']
        }

    def process_games_with_risk(self, games: List[Dict]) -> List[Dict]:
        """Process games with enhanced risk management."""
        recommendations = []

        for game in games:
            game_recommendations = []

            # Skip if game has started
            commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            if commence_time <= datetime.now(timezone.utc):
                continue

            for market in game.get('formatted_markets', []):
                for outcome in market.get('data', []):
                    # Validate the edge
                    validation = self.validate_edge(game, market, outcome)

                    # Create recommendation
                    recommendation = self.create_bet_recommendation(
                        game, market, outcome, validation
                    )

                    if validation['is_valid']:
                        game_recommendations.append(recommendation)

            # Add best recommendations for this game
            if game_recommendations:
                # Sort by confidence and take top 2
                game_recommendations.sort(key=lambda x: x['confidence'], reverse=True)
                recommendations.extend(game_recommendations[:2])

        return recommendations