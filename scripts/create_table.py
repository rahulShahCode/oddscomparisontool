import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('odds.db')
c = conn.cursor()

# Create table for storing pinnacle lines with additional columns 'sport_key' and 'outcome_name'
c.execute('''
CREATE TABLE IF NOT EXISTS pinnacle_lines (
    event_id TEXT PRIMARY KEY,
    event_name TEXT,
    sport_key TEXT,
    market_type TEXT,
    outcome_name TEXT,
    line_value REAL,
    odds REAL,
    event_time DATETIME,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Commit and close the connection
conn.commit()
conn.close()
