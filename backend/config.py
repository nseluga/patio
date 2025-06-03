# Import os to access environment variables
import os

# Set the PostgreSQL database connection string (using default db name 'patio')
DATABASE_URL = "postgresql://postgres:Babson232323!@localhost:5432/patio"   # For Mike, figure out the username and pswd, or alternative way to do this url

# Set the secret key for JWT; fallback to default if not set in environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
