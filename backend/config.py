# Import os to access environment variables
import os

# Set the PostgreSQL database connection string from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Set the secret key for JWT from environment variable.
# No fallback — a missing SECRET_KEY is a hard startup failure; never silently use a weak default.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Set it to a long random string before starting the server."
    )
