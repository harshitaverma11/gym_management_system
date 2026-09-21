"""Create the PostgreSQL tables used by the GymPro API."""
from database import get_connection


TABLES = (
    """
    CREATE TABLE IF NOT EXISTS members (
        member_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        age INT,
        gender CHAR(1) DEFAULT 'M',
        phone VARCHAR(20) NOT NULL,
        email VARCHAR(100) DEFAULT '',
        address TEXT,
        status VARCHAR(20) DEFAULT 'active',
        join_date DATE DEFAULT CURRENT_DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trainers (
        trainer_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        phone VARCHAR(20) DEFAULT '',
        email VARCHAR(100) DEFAULT '',
        specialization VARCHAR(100) DEFAULT '',
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        payment_id SERIAL PRIMARY KEY,
        member_id INT REFERENCES members(member_id) ON DELETE SET NULL,
        amount DECIMAL(10, 2) NOT NULL,
        payment_date DATE DEFAULT CURRENT_DATE,
        method VARCHAR(30) DEFAULT 'cash',
        status VARCHAR(20) DEFAULT 'paid',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plans (
        plan_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        duration_days INT NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        description TEXT,
        features TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memberships (
        membership_id SERIAL PRIMARY KEY,
        member_id INT NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
        plan_id INT NOT NULL REFERENCES plans(plan_id) ON DELETE RESTRICT,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        paid_amount DECIMAL(10, 2) DEFAULT 0,
        payment_method VARCHAR(30) DEFAULT 'cash',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id SERIAL PRIMARY KEY,
        member_id INT NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
        check_in TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        check_out TIMESTAMP,
        notes VARCHAR(255) DEFAULT '',
        marked_by VARCHAR(50) DEFAULT 'admin'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        notif_id SERIAL PRIMARY KEY,
        type VARCHAR(30) NOT NULL,
        title VARCHAR(200) NOT NULL,
        message TEXT,
        member_id INT REFERENCES members(member_id) ON DELETE CASCADE,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


# Links a signed-up user to their member profile so GET /members includes them.
MIGRATIONS = (
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(user_id) ON DELETE SET NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS members_user_id_key ON members(user_id) WHERE user_id IS NOT NULL",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS city VARCHAR(100) DEFAULT ''",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS emergency_contact VARCHAR(20) DEFAULT ''",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100) DEFAULT ''",
)


def ensure_core_tables():
    conn = get_connection()
    if not conn:
        print("[setup] Cannot reach database — skipping core tables")
        return

    try:
        with conn:
            with conn.cursor() as cursor:
                for statement in TABLES:
                    cursor.execute(statement)
                for statement in MIGRATIONS:
                    cursor.execute(statement)
        print("[setup] Core PostgreSQL tables OK")
    except Exception as error:
        print(f"[setup] Core tables error: {error}")
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_core_tables()
