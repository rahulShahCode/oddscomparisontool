"""
Configuration for sharp sportsbooks and their characteristics.
"""

SHARP_SPORTSBOOKS = {
    "tier_1_sharps": {
        # The sharpest books - their lines are most efficient
        "pinnacle": {
            "trust_score": 10,
            "liquidity": "very_high",
            "accepts_pros": True,
            "best_for": ["NFL", "NBA", "MLB", "Soccer"],
            "api_available": True,
            "notes": "Gold standard for sharp lines, highest limits"
        },
        "circa": {
            "trust_score": 9.5,
            "liquidity": "very_high",
            "accepts_pros": True,
            "best_for": ["NFL", "NCAAF"],
            "api_available": False,
            "notes": "Vegas-based, massive NFL limits, very sharp"
        },
        "bookmaker": {
            "trust_score": 9,
            "liquidity": "high",
            "accepts_pros": True,
            "best_for": ["NFL", "NBA", "MLB"],
            "api_available": True,
            "notes": "CRIS/Bookmaker.eu - early lines, sharp action"
        }
    },

    "tier_2_sharps": {
        # Still sharp but might have slightly softer lines
        "betonline": {
            "trust_score": 8,
            "liquidity": "high",
            "accepts_pros": True,
            "best_for": ["NFL", "NCAAF", "NBA"],
            "api_available": False,
            "notes": "Good for early lines, accepts US players"
        },
        "lowvig": {
            "trust_score": 8,
            "liquidity": "medium",
            "accepts_pros": True,
            "best_for": ["NFL", "NBA"],
            "api_available": True,
            "notes": "Low juice lines, good for line shopping"
        },
        "heritage": {
            "trust_score": 7.5,
            "liquidity": "medium",
            "accepts_pros": True,
            "best_for": ["NFL", "NCAAF"],
            "api_available": False,
            "notes": "Reduced juice, good overnight lines"
        }
    },

    "market_makers": {
        # Books that help set the market
        "westgate": {
            "trust_score": 8.5,
            "liquidity": "high",
            "accepts_pros": True,
            "best_for": ["NFL"],
            "api_available": False,
            "notes": "Las Vegas SuperBook, posts NFL lines early"
        },
        "stations": {
            "trust_score": 7.5,
            "liquidity": "medium",
            "accepts_pros": True,
            "best_for": ["NFL", "NCAAF"],
            "api_available": False,
            "notes": "Station Casinos, good for local Vegas action"
        }
    },

    "recreational_books": {
        # Where to find value against sharp lines
        "fanduel": {
            "trust_score": 6,
            "liquidity": "very_high",
            "accepts_pros": False,
            "best_for": ["NFL same-game parlays", "boosts"],
            "api_available": True,
            "notes": "Slow to move lines, good for player props"
        },
        "draftkings": {
            "trust_score": 6,
            "liquidity": "very_high",
            "accepts_pros": False,
            "best_for": ["NFL props", "live betting"],
            "api_available": True,
            "notes": "High limits, sometimes slow on line moves"
        },
        "betmgm": {
            "trust_score": 5.5,
            "liquidity": "high",
            "accepts_pros": False,
            "best_for": ["NFL spreads", "totals"],
            "api_available": True,
            "notes": "Often has different lines than consensus"
        },
        "caesars": {
            "trust_score": 5.5,
            "liquidity": "high",
            "accepts_pros": False,
            "best_for": ["NFL futures", "props"],
            "api_available": True,
            "notes": "William Hill platform, unique lines sometimes"
        },
        "espnbet": {
            "trust_score": 5,
            "liquidity": "medium",
            "accepts_pros": False,
            "best_for": ["NFL casual bets"],
            "api_available": True,
            "notes": "Newer book, sometimes slow to adjust"
        }
    }
}

NFL_SPECIFIC_STRATEGY = {
    "key_numbers": {
        "spreads": [3, 7, 10, 14, 17, 21],  # Most common margins of victory
        "totals": [37, 40, 41, 43, 44, 47, 51],  # Common total scores
        "importance": "CRITICAL - buying on/off these numbers is valuable"
    },

    "timing": {
        "best_bet_times": [
            "Sunday night/Monday morning after lines release",
            "Tuesday-Wednesday before sharp money hits",
            "Friday for contrarian unders (public bets overs)",
            "60-90 minutes before kickoff (recreational money moves)"
        ],
        "avoid_times": [
            "Saturday (lines are sharpest)",
            "Right after injury news (lines moving fast)"
        ]
    },

    "market_dynamics": {
        "public_tendencies": [
            "Overs (especially primetime)",
            "Favorites (especially home)",
            "Popular teams (Cowboys, Chiefs, Bills)",
            "Previous week winners"
        ],
        "sharp_tendencies": [
            "Unders in divisional games",
            "Road dogs getting 7+",
            "Fading public teams",
            "Under on high totals (48+)"
        ]
    },

    "edges_to_exploit": {
        "teaser_opportunities": "Cross 3 and 7 on multiple games",
        "primetime_unders": "Public overbets primetime overs",
        "division_dogs": "Divisional underdogs +7 or more",
        "weather_impact": "Wind/snow creates under value",
        "backup_qb": "Market overreacts to backup QBs"
    }
}

def get_sharp_consensus(odds_data: dict, min_books: int = 3) -> dict:
    """
    Get consensus sharp line from multiple sharp books.
    More reliable than using single book.
    """
    sharp_lines = []
    weights = []

    for book, data in odds_data.items():
        if book in SHARP_SPORTSBOOKS["tier_1_sharps"]:
            sharp_lines.append(data)
            weights.append(SHARP_SPORTSBOOKS["tier_1_sharps"][book]["trust_score"])
        elif book in SHARP_SPORTSBOOKS["tier_2_sharps"]:
            sharp_lines.append(data)
            weights.append(SHARP_SPORTSBOOKS["tier_2_sharps"][book]["trust_score"])

    if len(sharp_lines) < min_books:
        return None

    # Weight average based on trust scores
    weighted_line = sum(l * w for l, w in zip(sharp_lines, weights)) / sum(weights)

    return {
        "consensus_line": weighted_line,
        "num_books": len(sharp_lines),
        "confidence": min(len(sharp_lines) * 20, 100)  # More books = more confidence
    }

def is_line_sharp(spread: float, total: float, sport: str = "NFL") -> bool:
    """Check if a line appears to be sharp based on characteristics."""

    if sport == "NFL":
        # Check if line is on/near key number
        key_spreads = NFL_SPECIFIC_STRATEGY["key_numbers"]["spreads"]
        key_totals = NFL_SPECIFIC_STRATEGY["key_numbers"]["totals"]

        # Sharp lines often sit exactly on key numbers
        spread_is_key = any(abs(spread - key) < 0.5 for key in key_spreads)
        total_is_key = any(abs(total - key) < 0.5 for key in key_totals)

        return spread_is_key or total_is_key

    return True