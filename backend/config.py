import os

DATABASE_URL = os.getenv("DATABASE_URL", "dbname=yourdb user=youruser password=yourpass host=localhost")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
