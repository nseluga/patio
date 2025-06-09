# Import os to access environment variables
import os

# Set the PostgreSQL database connection string (using default db name 'patio')
DATABASE_URL = "postgresql://postgres.dwnntzbzadiytktiwena:patiobestspotat5cs@aws-0-us-east-2.pooler.supabase.com:6543/postgres"

# Set the secret key for JWT; fallback to default if not set in environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
