from backend.db import get_db

def add_weekly_caps():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE players SET caps_balance = caps_balance + 100")
    conn.commit()
    cur.close()
    conn.close()
    print("✅ 100 caps added to all players.")

# if __name__ == "__main__":
#     add_weekly_caps()
# We cannot really implement this until we have a backend running 24/7
