# Import the get_db function to establish a database connection
from db import get_db

# Function to create the 'players' table if it doesn't already exist
def create_players_table():
    # Connect to the database and open a cursor
    conn = get_db()
    cur = conn.cursor()

    # Execute SQL to create the players table with relevant fields
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,                  -- Auto-incrementing player ID
            username TEXT UNIQUE NOT NULL,          -- Unique username, required
            email TEXT UNIQUE NOT NULL,             -- Unique email, required
            password_hash TEXT NOT NULL,            -- Hashed password, required
            profile_pic_url TEXT,                   -- Optional URL for profile picture
            caps_balance INT DEFAULT 0,             -- In-app currency balance, default 0
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp of account creation
        )
    ''')

    # Commit changes and close the connection
    conn.commit()
    cur.close()
    conn.close()

    # Confirm table creation
    print("✅ players table created!")

# Run the function only if the script is executed directly
if __name__ == "__main__":
    create_players_table()
