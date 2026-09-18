"""
Kept for backwards compatibility. Full setup is in setup.py.
"""
from database import get_connection


def ensure_workouts_table():
    conn = get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                workout_id   SERIAL          PRIMARY KEY,
                name         VARCHAR(100)    NOT NULL,
                category     VARCHAR(50)     DEFAULT 'General',
                duration     INT,
                difficulty   VARCHAR(20)     DEFAULT 'beginner',
                description  TEXT,
                exercises    TEXT,
                member_id    INT             DEFAULT NULL,
                created_date TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Check for missing columns (migration)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='workouts'
        """)
        cols = [row[0] for row in cursor.fetchall()]
        if 'exercises' not in cols:
            cursor.execute("ALTER TABLE workouts ADD COLUMN exercises TEXT")
            print("[setup] ✓ Added exercises column to workouts")
        if 'member_id' not in cols:
            cursor.execute("ALTER TABLE workouts ADD COLUMN member_id INT DEFAULT NULL")
            print("[setup] ✓ Added member_id column to workouts")

        # trainers: ensure email + specialization columns exist
        try:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='trainers'
            """)
            trainer_cols = [row[0] for row in cursor.fetchall()]
            if 'email' not in trainer_cols:
                cursor.execute("ALTER TABLE trainers ADD COLUMN email VARCHAR(100)")
                print("[setup] ✓ Added email column to trainers")
            if 'specialization' not in trainer_cols:
                cursor.execute("ALTER TABLE trainers ADD COLUMN specialization VARCHAR(100)")
                print("[setup] ✓ Added specialization column to trainers")
            if 'status' not in trainer_cols:
                cursor.execute("ALTER TABLE trainers ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
                print("[setup] ✓ Added status column to trainers")
        except Exception:
            pass

        # payments: ensure method + status columns exist
        try:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='payments'
            """)
            pay_cols = [row[0] for row in cursor.fetchall()]
            if 'method' not in pay_cols:
                cursor.execute("ALTER TABLE payments ADD COLUMN method VARCHAR(30) DEFAULT 'cash'")
                print("[setup] ✓ Added method column to payments")
            if 'status' not in pay_cols:
                cursor.execute("ALTER TABLE payments ADD COLUMN status VARCHAR(20) DEFAULT 'paid'")
                print("[setup] ✓ Added status column to payments")
        except Exception:
            pass

        # members: ensure status column exists
        try:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='members'
            """)
            mem_cols = [row[0] for row in cursor.fetchall()]
            if 'status' not in mem_cols:
                cursor.execute("ALTER TABLE members ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
                print("[setup] ✓ Added status column to members")
        except Exception:
            pass

        conn.commit()
        print("[setup] ✓ Workouts table OK")
    except Exception as e:
        print(f"[setup] ✗ Workouts table error: {e}")
    finally:
        cursor.close()
        conn.close()


# run migrations on import (called by app.py)
ensure_workouts_table()


if __name__ == "__main__":
    ensure_workouts_table()
