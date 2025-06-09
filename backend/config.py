# Import os to access environment variables
import os

# Set the PostgreSQL database connection string (using default db name 'patio')
DATABASE_URL = "postgresql://postgres:patiobestspotat5cs@db.dwnntzbzadiytktiwena.supabase.co:5432/postgres"

# Set the secret key for JWT; fallback to default if not set in environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
