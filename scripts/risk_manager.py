"""
Risk management module to prevent large losses and identify suspicious lines.
"""
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """Manages betting risk and identifies potential trap games."""

    def __init__(self, bankroll: float = 1000.0):
        self.bankroll = bankroll
        self.max_exposure_pct = 0.05  # Max 5% of bankroll on single bet
        self.daily_loss_limit_pct = 0.1  # Stop at 10% daily loss
        self.min_edge_thresholds = {
            'basketball_nba': 2.0,
            'baseball_mlb': 2.5,
            'americanfootball_nfl': 2.5,
            'americanfootball_ncaaf': 3.5,  # Higher threshold for college
            'icehockey_nhl': 2.5,
            'default': 3.0
        }
        self.daily_results = []

    def calculate_kelly_fraction(self, win_prob: float, odds: int) -> float:
        """
        Calculate Kelly Criterion for optimal bet sizing.
        Using fractional Kelly (25%) for safety.
        """
        if odds > 0:
            decimal_odds = 1 + (odds / 100)
        else:
            decimal_odds = 1 + (100 / abs(odds))

        # Kelly formula: f = (p * (odds + 1) - 1) / odds
        # Where p is true win probability
        kelly = (win_prob * decimal_odds - 1) / (decimal_odds - 1)

        # Use 25% Kelly for safety (reduces variance)
        fractional_kelly = kelly * 0.25

        # Cap at 5% of bankroll
        return min(fractional_kelly, self.max_exposure_pct)

    def get_min_edge_for_sport(self, sport: str) -> float:
        """Get minimum edge threshold for a sport."""
        return self.min_edge_thresholds.get(sport, self.min_edge_thresholds['default'])

    def is_suspicious_line(self, my_odds: int, pinnacle_odds: int,
                          market_type: str, sport: str) -> Tuple[bool, str]:
        """
        Detect potentially suspicious lines that might be traps.
        """
        edge = self.calculate_edge(my_odds, pinnacle_odds)

        # Red flags for suspicious lines
        if sport == 'americanfootball_ncaaf':
            # College football specific checks
            if edge > 8.0:
                return True, "Edge too large (>8%) - possible trap or stale line"

            # Check for unusual line movement patterns
            if market_type == 'spreads' and abs(my_odds + pinnacle_odds) > 30:
                return True, "Large odds discrepancy on spread - check for injuries/news"

        # General checks
        if edge > 10.0:
            return True, "Edge exceeds 10% - likely stale or incorrect line"

        # Check for one-sided action indicators
        if my_odds < -300 or pinnacle_odds < -300:
            if edge > 5.0:
                return True, "Large edge on heavy favorite - potential trap"

        return False, ""

    def calculate_edge(self, my_odds: int, pinnacle_odds: int) -> float:
        """Calculate the betting edge percentage."""
        my_prob = self.american_to_probability(my_odds)
        pin_prob = self.american_to_probability(pinnacle_odds)
        return pin_prob - my_prob

    def american_to_probability(self, odds: int) -> float:
        """Convert American odds to implied probability."""
        if odds > 0:
            return (100 / (odds + 100)) * 100
        else:
            return (-odds / (-odds + 100)) * 100

    def calculate_confidence_interval(self, edge: float, sample_size: int = 100) -> Tuple[float, float]:
        """
        Calculate confidence interval for the edge.
        Helps understand if edge is statistically significant.
        """
        # Standard error for betting edges (rough approximation)
        std_error = 100 / math.sqrt(sample_size)  # In percentage points

        # 95% confidence interval
        lower_bound = edge - (1.96 * std_error / 100)
        upper_bound = edge + (1.96 * std_error / 100)

        return lower_bound, upper_bound

    def should_place_bet(self, bet_info: Dict) -> Tuple[bool, str, float]:
        """
        Determine if a bet should be placed and the recommended stake.

        Returns:
            (should_bet, reason, recommended_stake_pct)
        """
        sport = bet_info.get('sport', 'default')
        edge = bet_info.get('edge', 0)
        my_odds = bet_info.get('my_odds', 0)
        pinnacle_odds = bet_info.get('pinnacle_odds', 0)
        market_type = bet_info.get('market_type', '')

        # Check minimum edge threshold
        min_edge = self.get_min_edge_for_sport(sport)
        if edge < min_edge:
            return False, f"Edge {edge:.2f}% below minimum {min_edge}%", 0

        # Check for suspicious lines
        is_suspicious, reason = self.is_suspicious_line(
            my_odds, pinnacle_odds, market_type, sport
        )
        if is_suspicious:
            return False, f"Suspicious line: {reason}", 0

        # Calculate confidence interval
        lower_ci, upper_ci = self.calculate_confidence_interval(edge)
        if lower_ci < 0:
            return False, f"Edge not statistically significant (CI: {lower_ci:.2f}% to {upper_ci:.2f}%)", 0

        # Check daily loss limit
        daily_loss = sum(self.daily_results)
        if daily_loss < -self.bankroll * self.daily_loss_limit_pct:
            return False, "Daily loss limit reached", 0

        # Calculate recommended stake
        win_prob = self.american_to_probability(pinnacle_odds) / 100
        kelly_stake = self.calculate_kelly_fraction(win_prob, my_odds)

        # Further reduce stake for college football
        if sport == 'americanfootball_ncaaf':
            kelly_stake *= 0.5  # Half Kelly for high variance

        return True, "Bet approved", kelly_stake

    def log_result(self, profit: float):
        """Log betting result for tracking."""
        self.daily_results.append(profit)
        self.bankroll += profit

    def reset_daily_tracking(self):
        """Reset daily tracking (call at start of each day)."""
        self.daily_results = []

    def get_stats(self) -> Dict:
        """Get current risk management statistics."""
        return {
            'bankroll': self.bankroll,
            'daily_pnl': sum(self.daily_results),
            'bets_today': len(self.daily_results),
            'at_daily_limit': sum(self.daily_results) < -self.bankroll * self.daily_loss_limit_pct
        }