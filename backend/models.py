# Import the get_db function to establish a database connection
from db import get_db

# Create the players table
def create_players_table():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            profile_pic_url TEXT,
            caps_balance INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    print("✅ players table created!")

# Create the bets table
def create_bets_table():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bets (
            id SERIAL PRIMARY KEY,
            poster_id INTEGER REFERENCES players(id),
            accepter_id INTEGER REFERENCES players(id),
            amount INT NOT NULL,
            game_type TEXT NOT NULL,
            line_type TEXT,
            line_number FLOAT,
            status TEXT DEFAULT 'open',  -- open, accepted, resolved, cancelled
            winner_id INTEGER REFERENCES players(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    print("✅ bets table created!")

# Run when script is executed directly
if __name__ == "__main__":
    create_players_table()
    create_bets_table()