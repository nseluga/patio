# Import psycopg2 to connect to a PostgreSQL database
import psycopg2

# Import the database connection string from config.py
from config import DATABASE_URL

# Function to create and return a new database connection
def get_db():
    return psycopg2.connect(DATABASE_URL)
