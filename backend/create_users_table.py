"""
Kept for backwards compatibility with app.py import.
All real setup is now in setup.py — run that first.
"""
from database import get_connection
from werkzeug.security import generate_password_hash


def ensure_users_table():
    conn = get_connection()
    if not conn:
        print("[setup] Cannot reach database — skipping users table check")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       SERIAL          PRIMARY KEY,
                username      VARCHAR(50)     UNIQUE NOT NULL,
                password_hash VARCHAR(255)    NOT NULL,
                role          VARCHAR(20)     DEFAULT 'member',
                created_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        if count == 0:
            for uname, pwd, role in [
                ('admin',    'admin123',   'admin'),
                ('trainer1', 'trainer123', 'trainer'),
                ('member1',  'member123',  'member'),
            ]:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
                    (uname, generate_password_hash(pwd), role)
                )
            conn.commit()
            print("[setup] ✓ Default users seeded (admin/trainer1/member1)")
        else:
            print(f"[setup] ✓ Users table OK ({count} accounts)")
    except Exception as e:
        print(f"[setup] ✗ Users table error: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    ensure_users_table()
