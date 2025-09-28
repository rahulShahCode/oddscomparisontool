"""
Enhanced version of the Odds Comparison Tool with NFL focus and sharp book consensus.

To run the enhanced version:
    python run_enhanced.py

To switch back to the original:
    python run.py
"""

from app.__init___enhanced import app

if __name__ == "__main__":
    print("=" * 60)
    print("🏈 Enhanced Odds Comparison Tool - NFL Focus")
    print("=" * 60)
    print("\nFeatures:")
    print("✓ Sharp book consensus (Pinnacle, Circa, Bookmaker)")
    print("✓ NFL key number analysis")
    print("✓ Risk management with Kelly Criterion")
    print("✓ Confidence scoring system")
    print("✓ Higher edge requirements (2.5%+ for NFL)")
    print("✓ Situational spot detection")
    print("\nStarting server on http://localhost:5001")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5001, debug=True)