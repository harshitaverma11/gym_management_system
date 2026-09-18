import psycopg2
import os

# ── PostgreSQL Database Configuration ─────────────────────────────────────────
# Use DATABASE_URL environment variable for Render, fallback to local dev setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/gym_management")
# ─────────────────────────────────────────────────────────────────────────────


def get_connection():
    """Return a live PostgreSQL connection, or None on failure."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as err:
        print(f"[DB] Connection error: {err}")
        return None


def test_connection():
    """Quick health-check — prints table info and returns True/False."""
    conn = get_connection()
    if not conn:
        print("[DB] ✗ Could not connect to database")
        return False

    cursor = conn.cursor()
    print("[DB] ✓ Connected to PostgreSQL database")

    for table in ("members", "trainers", "payments", "workouts", "users"):
        try:
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")
            cols = [row[0] for row in cursor.fetchall()]
            print(f"[DB]   {table}: {cols}")
        except Exception as e:
            print(f"[DB]   {table}: NOT FOUND ({e})")

    cursor.close()
    conn.close()
    return True


if __name__ == "__main__":
    test_connection()
