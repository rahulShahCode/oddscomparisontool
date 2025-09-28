# NFL Sharp Betting Improvements

## Overview
This branch contains significant improvements focused on NFL betting with sharp book consensus and advanced risk management.

## New Features

### 1. Sharp Book Consensus
- Aggregates lines from multiple sharp books (Pinnacle, Circa, Bookmaker, etc.)
- Weighted consensus based on book reputation
- Requires agreement from multiple sharp books before recommending a bet

### 2. NFL Key Number Analysis
- Identifies value when crossing key numbers (3, 7, 10, etc.)
- Adjusts edge calculations based on key number value
- Provides additional confidence when on the right side of key numbers

### 3. Enhanced Risk Management
- **Kelly Criterion betting** with 25% fractional Kelly for safety
- **Sport-specific edge requirements**:
  - NFL: 2.5-3% minimum
  - NCAAF: 4% minimum (higher variance)
  - NBA/MLB: 2.5-3% minimum
- **Daily stop-loss** at 10% of bankroll
- **Maximum bet sizing** varies by sport confidence

### 4. Situational Analysis
- Detects primetime games (more public action)
- Identifies divisional matchups (tend to go under)
- Flags public team bias (Cowboys, Chiefs, etc.)
- Warns about short week games (Thursday Night Football)

### 5. Confidence Scoring System
- Combines multiple factors:
  - Sharp book agreement
  - Key number value
  - Edge size
  - Situational factors
- Only recommends bets with 60%+ confidence

## File Structure

```
scripts/
├── get_data_enhanced.py      # Enhanced odds processor with sharp consensus
├── nfl_analyzer.py           # NFL-specific analysis and key numbers
├── risk_manager.py           # Kelly Criterion and bankroll management
├── sharp_books_config.py     # Sharp book configurations and trust scores
└── enhanced_processor.py     # Main processing engine

app/
├── __init___enhanced.py      # Enhanced Flask application
└── templates/
    └── odds_enhanced.html    # New UI with confidence indicators
```

## How to Use

### Run the Enhanced Version
```bash
python run_enhanced.py
```

### Switch Back to Original
```bash
python run.py
```

### Configuration
Edit `data/safer_config.json` to adjust:
- Bankroll size
- Edge thresholds
- Maximum bet percentages
- Sport-specific settings

## Key Improvements Over Original

1. **Higher Edge Requirements**: Increased from 1-1.5% to 2.5-4% depending on sport
2. **Multiple Sharp Book Validation**: Not just Pinnacle anymore
3. **Statistical Confidence**: Uses confidence intervals to validate edges
4. **Bankroll Protection**: Automatic stop-loss and position sizing
5. **NFL Optimization**: Key numbers and situational spots for NFL

## Risk Warnings

⚠️ **Important**:
- Even with these improvements, sports betting carries inherent risk
- Start with small stakes to validate the system
- Track all bets to measure actual vs expected performance
- The system is more conservative but not guaranteed profitable
- NCAAF remains high-risk even with 4% edge requirement

## API Usage Note
The enhanced version may use more API calls due to:
- Fetching odds from more bookmakers
- Checking alternate lines for better comparisons

Monitor your API quota usage carefully.

## Testing Recommendations

1. **Paper trade first**: Track hypothetical bets for 2-4 weeks
2. **Start small**: Use 0.5-1% of bankroll per bet initially
3. **Focus on NFL**: Most reliable with best data
4. **Track CLV**: Monitor if your bets beat the closing line
5. **Review weekly**: Analyze what's working and what isn't

## Future Enhancements

- [ ] Live betting analysis
- [ ] Weather impact calculations
- [ ] Injury report integration
- [ ] Historical backtesting system
- [ ] Closing line value tracking
- [ ] Automated bet placement via API