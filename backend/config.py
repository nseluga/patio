# Import os to access environment variables
import os

# Set the PostgreSQL database connection string from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Set the secret key for JWT from environment variable
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
