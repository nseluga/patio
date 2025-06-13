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
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            poster TEXT NOT NULL,
            posterId TEXT NOT NULL REFERENCES players(id),
            accepterId TEXT REFERENCES players(id),

            timePosted TIMESTAMP NOT NULL DEFAULT NOW(),
            gameType TEXT NOT NULL CHECK (gameType IN ('Score', 'Shots Made', 'Other')),
            gamePlayed TEXT NOT NULL CHECK (gamePlayed IN ('Caps', 'Pong', 'Beerball', 'Campus Golf', 'Other')),
            amount INTEGER NOT NULL,
            matchup TEXT NOT NULL,
            lineType TEXT NOT NULL CHECK (lineType in ('Over', 'Under')),
            lineNumber FLOAT NOT NULL,

            gameSize TEXT CHECK (gameSize IN ('1v1', '2v2', '3v3')),
            yourTeamA JSONB,
            yourTeamB JSONB,
            oppTeamA JSONB,
            oppTeamB JSONB,
            yourScoreA INTEGER,
            yourScoreB INTEGER,
            oppScoreA INTEGER,
            oppScoreB INTEGER,

            yourPlayer TEXT,
            yourShots INTEGER,
            oppPlayer TEXT,
            oppShots INTEGER,

            yourOutcome TEXT,
            oppOutcome INTEGER
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