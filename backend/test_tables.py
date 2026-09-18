from database import get_connection

conn = get_connection()
if conn:
    cursor = conn.cursor()
    # Check trainers table
    try:
        cursor.execute("DESCRIBE trainers")
        print("✓ Trainers table exists:")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  - {col[0]} ({col[1]})")
    except Exception as e:
        print(f"✗ Trainers table error: {e}")
    
    # Check payments table
    try:
        cursor.execute("DESCRIBE payments")
        print("✓ Payments table exists:")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  - {col[0]} ({col[1]})")
    except Exception as e:
        print(f"✗ Payments table error: {e}")
    
    # Check workouts table
    try:
        cursor.execute("DESCRIBE workouts")
        print("✓ Workouts table exists:")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  - {col[0]} ({col[1]})")
    except Exception as e:
        print(f"✗ Workouts table error: {e}")
    
    # Check users table
    try:
        cursor.execute("DESCRIBE users")
        print("✓ Users table exists:")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  - {col[0]} ({col[1]})")
    except Exception as e:
        print(f"✗ Users table error: {e}")
    
    cursor.close()
    conn.close()
