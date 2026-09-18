"""
GymPro — setup.py  (run once: python setup.py)
Creates all tables + seeds default accounts & membership plans.
"""
from database import get_connection
from werkzeug.security import generate_password_hash


def run_setup():
    conn = get_connection()
    if not conn:
        print("\n✗ Cannot connect — check database.py credentials\n")
        return False

    cur = conn.cursor()

    def run(label, sql):
        try:
            cur.execute(sql); conn.commit()
            print(f"  ✓ {label}")
        except Exception as e:
            print(f"  ~ {label}: {e}")

    print("\n" + "="*50)
    print("  GymPro Database Setup")
    print("="*50 + "\n")

    # core tables
    run("members", "CREATE TABLE IF NOT EXISTS members (member_id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) NOT NULL, age INT, gender CHAR(1) DEFAULT 'M', phone VARCHAR(20) NOT NULL, email VARCHAR(100) DEFAULT '', address TEXT, status VARCHAR(20) DEFAULT 'active', join_date DATE DEFAULT (CURRENT_DATE), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    run("trainers", "CREATE TABLE IF NOT EXISTS trainers (trainer_id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) NOT NULL, phone VARCHAR(20) DEFAULT '', email VARCHAR(100) DEFAULT '', specialization VARCHAR(100) DEFAULT '', status VARCHAR(20) DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    run("payments", "CREATE TABLE IF NOT EXISTS payments (payment_id INT PRIMARY KEY AUTO_INCREMENT, member_id INT, amount DECIMAL(10,2) NOT NULL, payment_date DATE DEFAULT (CURRENT_DATE), method VARCHAR(30) DEFAULT 'cash', status VARCHAR(20) DEFAULT 'paid', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE SET NULL)")
    run("workouts", "CREATE TABLE IF NOT EXISTS workouts (workout_id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) NOT NULL, category VARCHAR(50) DEFAULT 'General', duration INT, difficulty VARCHAR(20) DEFAULT 'beginner', description TEXT, exercises TEXT, member_id INT DEFAULT NULL, created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    run("users", "CREATE TABLE IF NOT EXISTS users (user_id INT PRIMARY KEY AUTO_INCREMENT, username VARCHAR(50) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, role VARCHAR(20) DEFAULT 'member', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

    # new tables
    run("plans", "CREATE TABLE IF NOT EXISTS plans (plan_id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) NOT NULL, duration_days INT NOT NULL, price DECIMAL(10,2) NOT NULL, description TEXT, features TEXT, is_active TINYINT(1) DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    run("memberships", "CREATE TABLE IF NOT EXISTS memberships (membership_id INT PRIMARY KEY AUTO_INCREMENT, member_id INT NOT NULL, plan_id INT NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL, status VARCHAR(20) DEFAULT 'active', paid_amount DECIMAL(10,2) DEFAULT 0, payment_method VARCHAR(30) DEFAULT 'cash', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE, FOREIGN KEY (plan_id) REFERENCES plans(plan_id) ON DELETE RESTRICT)")
    run("attendance", "CREATE TABLE IF NOT EXISTS attendance (attendance_id INT PRIMARY KEY AUTO_INCREMENT, member_id INT NOT NULL, check_in DATETIME DEFAULT CURRENT_TIMESTAMP, check_out DATETIME DEFAULT NULL, notes VARCHAR(255) DEFAULT '', marked_by VARCHAR(50) DEFAULT 'admin', FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE)")
    run("notifications", "CREATE TABLE IF NOT EXISTS notifications (notif_id INT PRIMARY KEY AUTO_INCREMENT, type VARCHAR(30) NOT NULL, title VARCHAR(200) NOT NULL, message TEXT, member_id INT DEFAULT NULL, is_read TINYINT(1) DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE)")

    # migrations
    print("\n  Migrations…")
    for table, col, defn in [
        ("payments","method","VARCHAR(30) DEFAULT 'cash'"),
        ("payments","status","VARCHAR(20) DEFAULT 'paid'"),
        ("payments","notes","TEXT"),
        ("trainers","email","VARCHAR(100) DEFAULT ''"),
        ("trainers","specialization","VARCHAR(100) DEFAULT ''"),
        ("trainers","status","VARCHAR(20) DEFAULT 'active'"),
        ("members","status","VARCHAR(20) DEFAULT 'active'"),
        ("members","email","VARCHAR(100) DEFAULT ''"),
        ("workouts","exercises","TEXT"),
        ("workouts","member_id","INT DEFAULT NULL"),
        ("workouts","difficulty","VARCHAR(20) DEFAULT 'beginner'"),
        ("workouts","description","TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            conn.commit(); print(f"  ✓ Added {table}.{col}")
        except Exception:
            pass

    # seed plans
    print("\n  Plans…")
    try:
        cur.execute("SELECT COUNT(*) FROM plans")
        if cur.fetchone()[0] == 0:
            for name, days, price, desc, feat in [
                ("Monthly",    30,  999,  "1 month full access",   "Gym access,Locker,Free WiFi"),
                ("Quarterly",  90,  2499, "3 months full access",  "Gym access,Locker,Free WiFi,Diet plan"),
                ("Half Yearly",180, 4499, "6 months full access",  "Gym access,Locker,Free WiFi,Diet plan,1 PT session"),
                ("Yearly",     365, 7999, "12 months full access", "Gym access,Locker,Free WiFi,Diet plan,4 PT sessions,Body analysis"),
                ("Student",    30,  699,  "Student discount plan", "Gym access,Free WiFi"),
            ]:
                cur.execute(
                    "INSERT INTO plans (name,duration_days,price,description,features) VALUES (%s,%s,%s,%s,%s)",
                    (name, days, price, desc, feat)
                )
            conn.commit()
            print("  ✓ 5 default plans created")
    except Exception as e:
        print(f"  ~ Plans: {e}")

    # seed users
    print("\n  Users…")
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        existing = cur.fetchone()[0]
        for uname, pwd, role in [("admin","admin123","admin"),("trainer1","trainer123","trainer"),("member1","member123","member")]:
            try:
                cur.execute("INSERT INTO users (username,password_hash,role) VALUES (%s,%s,%s)",
                            (uname, generate_password_hash(pwd), role))
                conn.commit(); print(f"  ✓ Created {uname}")
            except Exception:
                cur.execute("UPDATE users SET password_hash=%s WHERE username=%s",
                            (generate_password_hash(pwd), uname))
                conn.commit(); print(f"  ✓ Reset {uname} password")
    except Exception as e:
        print(f"  ~ Users: {e}")

    cur.close(); conn.close()
    print("\n  Done! Start server: python app.py\n")
    return True


if __name__ == "__main__":
    run_setup()
