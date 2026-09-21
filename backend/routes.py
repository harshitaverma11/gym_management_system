"""
GymPro — routes.py
All API route handlers. Authentication via X-User header.
"""
from flask import jsonify, request
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json, re, logging

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_current_user():
    """Read authenticated user from X-User header."""
    raw = request.headers.get("X-User", "")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return None


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required."}), 401
            if user.get("role") not in roles:
                return jsonify({
                    "error": f"Access denied. This action requires: {', '.join(roles)}"
                }), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def db():
    conn = get_connection()
    if not conn:
        raise Exception("Database connection failed. Please try again.")
    return conn


def serialize_row(row):
    """Convert datetime/date objects in a dict to ISO strings."""
    if isinstance(row, dict):
        return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
    return row


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH — PUBLIC (no decorators)
# ══════════════════════════════════════════════════════════════════════════════

def login():
    data      = request.get_json(force=True, silent=True) or {}
    username  = (data.get("username") or "").strip()
    password  = data.get("password") or ""
    role_hint = (data.get("role") or "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Login DB error: {e}")
        return jsonify({"error": "Database error during login."}), 500

    if not user:
        return jsonify({"error": "Invalid username or password."}), 401

    if not check_password_hash(user.get("password_hash", ""), password):
        return jsonify({"error": "Invalid username or password."}), 401

    if role_hint and user.get("role") != role_hint:
        return jsonify({
            "error": f"This account has role '{user.get('role')}', not '{role_hint}'."
        }), 403

    logger.info(f"Login: {username} ({user.get('role')})")
    return jsonify({
        "message": "Login successful",
        "status":  "success",
        "user": {
            "username": user["username"],
            "role":     user["role"],
            "user_id":  user.get("user_id"),
        }
    })


def _parse_member_profile(data):
    """Validate the shared member profile fields used by both signup and Admin → Add Member."""
    profile = {
        "name":              (data.get("name") or data.get("full_name") or "").strip(),
        "phone":             (data.get("phone") or "").strip(),
        "gender":            (data.get("gender") or "M")[:1].upper(),
        "address":           (data.get("address") or "").strip(),
        "city":              (data.get("city") or "").strip(),
        "emergency_contact": (data.get("emergency_contact") or "").strip(),
        "join_date":         data.get("join_date") or None,
    }

    if not profile["name"]:
        return None, "Full name is required."
    if not profile["phone"]:
        return None, "Phone number is required."
    if not profile["address"]:
        return None, "Address is required."
    if not profile["city"]:
        return None, "City is required."
    if not profile["emergency_contact"]:
        return None, "Emergency contact is required."

    age_raw = data.get("age")
    try:
        age = int(age_raw)
    except (TypeError, ValueError):
        return None, "A valid age is required."
    if age < 10 or age > 100:
        return None, "Age must be between 10 and 100."
    profile["age"] = age

    return profile, None


def signup():
    data     = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or data.get("confirmPassword") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    if len(username) < 3 or len(username) > 50:
        return jsonify({"error": "Username must be between 3 and 50 characters."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if confirm_password and password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    profile, error = _parse_member_profile(data)
    if error:
        return jsonify({"error": error}), 400

    conn = None
    try:
        conn = db()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "That username/email is already registered."}), 409

        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'member') RETURNING user_id",
            (username, generate_password_hash(password))
        )
        user_id = cursor.fetchone()[0]

        # Every member account must have a matching row in members so it shows up in Admin → Members.
        email = username if "@" in username else ""
        cursor.execute(
            "INSERT INTO members (name, age, gender, phone, email, address, city, emergency_contact, "
            "join_date, status, user_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,CURRENT_DATE),'active',%s) "
            "ON CONFLICT (user_id) WHERE user_id IS NOT NULL DO NOTHING",
            (profile["name"], profile["age"], profile["gender"], profile["phone"], email,
             profile["address"], profile["city"], profile["emergency_contact"], profile["join_date"], user_id)
        )

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "message": "Member account created.",
            "status": "success",
            "user": {"user_id": user_id, "username": username, "role": "member"}
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            return jsonify({"error": "That username is already registered."}), 409
        logger.error(f"Signup DB error: {e}")
        return jsonify({"error": "Could not create member account."}), 500


def logout():
    user = get_current_user()
    if user:
        logger.info(f"Logout: {user.get('username')}")
    return jsonify({"message": "Logged out successfully.", "status": "success"})


@login_required
@role_required("admin")
def add_user():
    data     = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role     = (data.get("role") or "trainer").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400
    if role != "trainer":
        return jsonify({"error": "This endpoint creates trainer accounts only."}), 400

    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (%s,%s,%s,NOW())",
            (username, generate_password_hash(password), role)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Could not create user: {str(e)}"}), 400

    return jsonify({"message": f"User '{username}' created.", "status": "success"}), 201


# ══════════════════════════════════════════════════════════════════════════════
#  MEMBERS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer", "member")
def get_members():
    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM members ORDER BY member_id DESC")
        rows = [serialize_row(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"get_members: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def add_member():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or data.get("confirmPassword") or ""

    if not username:
        return jsonify({"error": "Username/email is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if confirm_password and password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    profile, error = _parse_member_profile(data)
    if error:
        return jsonify({"error": error}), 400

    conn = None
    try:
        conn = db()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "That username/email is already used."}), 409

        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'member') RETURNING user_id",
            (username, generate_password_hash(password))
        )
        user_id = cursor.fetchone()[0]

        email = (data.get("email") or "").strip() or (username if "@" in username else "")
        cursor.execute(
            "INSERT INTO members (name, age, gender, phone, email, address, city, emergency_contact, "
            "join_date, status, user_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,CURRENT_DATE),%s,%s) "
            "RETURNING member_id",
            (profile["name"], profile["age"], profile["gender"], profile["phone"], email,
             profile["address"], profile["city"], profile["emergency_contact"], profile["join_date"],
             data.get("status") or "active", user_id)
        )
        new_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Member added: {profile['name']} (id={new_id}, user={user_id})")
        return jsonify({
            "message": "Member added with login account.",
            "status": "success",
            "id": new_id
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            return jsonify({"error": "That username/email is already used."}), 409
        logger.error(f"add_member: {e}")
        return jsonify({"error": "Could not create member account."}), 500


@login_required
@role_required("admin")
def update_member(id):
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE members SET name=%s,age=%s,gender=%s,phone=%s,email=%s,address=%s,"
            "city=%s,emergency_contact=%s,status=%s WHERE member_id=%s",
            (data.get("name"),
             data.get("age") or None,
             (data.get("gender") or "M")[:1].upper(),
             data.get("phone"),
             data.get("email") or "",
             data.get("address") or "",
             data.get("city") or "",
             data.get("emergency_contact") or "",
             data.get("status") or "active",
             id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Member updated.", "status": "success"})
    except Exception as e:
        logger.error(f"update_member {id}: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def delete_member(id):
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM members WHERE member_id=%s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Member deleted: id={id}")
        return jsonify({"message": "Member deleted.", "status": "success"})
    except Exception as e:
        logger.error(f"delete_member {id}: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  TRAINERS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer")
def get_trainers():
    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trainers ORDER BY trainer_id DESC")
        rows = [serialize_row(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"get_trainers: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def add_trainer():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not name:
        return jsonify({"error": "Trainer name is required."}), 400
    if not username:
        return jsonify({"error": "Username or email is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    conn = None
    try:
        conn = db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "That username/email is already used."}), 409

        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'trainer') RETURNING user_id",
            (username, generate_password_hash(password))
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO trainers (name,phone,email,specialization,status) VALUES (%s,%s,%s,%s,%s) RETURNING trainer_id",
            (name,
             (data.get("phone") or "").strip(),
             (data.get("email") or "").strip(),
             (data.get("specialization") or "").strip(),
             data.get("status") or "active")
        )
        trainer_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Trainer added: {name} (id={trainer_id}, user={user_id})")
        return jsonify({"message": "Trainer added with login account.", "status": "success", "id": trainer_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"add_trainer: {e}")
        return jsonify({"error": "Could not create trainer account and profile."}), 500


@login_required
@role_required("admin")
def update_trainer(id):
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trainers SET name=%s,phone=%s,email=%s,specialization=%s WHERE trainer_id=%s",
            (data.get("name"),
             data.get("phone") or "",
             data.get("email") or "",
             data.get("specialization") or "",
             id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Trainer updated.", "status": "success"})
    except Exception as e:
        logger.error(f"update_trainer {id}: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def delete_trainer(id):
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trainers WHERE trainer_id=%s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Trainer deleted: id={id}")
        return jsonify({"message": "Trainer deleted.", "status": "success"})
    except Exception as e:
        logger.error(f"delete_trainer {id}: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  PAYMENTS
# ══════════════════════════════════════════════════════════════════════════════

PAYMENT_MODES    = ("cash", "online")
PAYMENT_STATUSES = ("pending", "paid", "rejected")


def _own_member_id(cursor, user):
    """Resolve the member_id linked to the currently logged-in member's account."""
    cursor.execute("SELECT member_id FROM members WHERE user_id = %s", (user.get("user_id"),))
    row = cursor.fetchone()
    return row[0] if row else None


@login_required
@role_required("admin", "trainer", "member")
def get_payments():
    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)
        user   = get_current_user()

        if user.get("role") == "member":
            plain = conn.cursor()
            member_id = _own_member_id(plain, user)
            plain.close()
            if not member_id:
                cursor.close()
                conn.close()
                return jsonify([])
            cursor.execute("""
                SELECT p.*, m.name AS member_name
                FROM payments p
                LEFT JOIN members m ON p.member_id = m.member_id
                WHERE p.member_id = %s
                ORDER BY p.payment_date DESC
            """, (member_id,))
        else:
            cursor.execute("""
                SELECT p.*, m.name AS member_name
                FROM payments p
                LEFT JOIN members m ON p.member_id = m.member_id
                ORDER BY p.payment_date DESC
            """)

        rows = [serialize_row(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"get_payments: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def add_payment():
    data      = request.get_json(force=True, silent=True) or {}
    member_id = data.get("member_id")
    amount    = data.get("amount")
    mode      = (data.get("method") or data.get("payment_mode") or "cash").strip().lower()
    status    = (data.get("status") or "paid").strip().lower()
    txn_id    = (data.get("transaction_id") or "").strip()

    if not member_id:
        return jsonify({"error": "Member ID is required."}), 400
    if not amount or float(amount) <= 0:
        return jsonify({"error": "A valid amount is required."}), 400
    if mode not in PAYMENT_MODES:
        return jsonify({"error": "Payment mode must be Cash or Online."}), 400
    if status not in PAYMENT_STATUSES:
        return jsonify({"error": "Status must be Pending, Paid, or Rejected."}), 400
    if mode == "online" and not txn_id:
        return jsonify({"error": "Transaction ID is required for online payments."}), 400
    if mode == "cash":
        txn_id = ""

    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO payments (member_id,amount,payment_date,method,status,transaction_id,notes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING payment_id",
            (int(member_id),
             float(amount),
             data.get("date") or None,
             mode,
             status,
             txn_id,
             data.get("notes") or None)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Payment recorded: member={member_id} amount={amount} (id={new_id})")
        return jsonify({"message": "Payment recorded.", "status": "success", "id": new_id}), 201
    except Exception as e:
        logger.error(f"add_payment: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("member")
def member_add_payment():
    """Member submits a UPI transaction reference for an Online payment; always starts Pending."""
    data   = request.get_json(force=True, silent=True) or {}
    amount = data.get("amount")
    txn_id = (data.get("transaction_id") or "").strip()

    if not amount or float(amount) <= 0:
        return jsonify({"error": "A valid amount is required."}), 400
    if not txn_id:
        return jsonify({"error": "UPI transaction/reference ID is required."}), 400

    try:
        conn   = db()
        cursor = conn.cursor()
        member_id = _own_member_id(cursor, get_current_user())
        if not member_id:
            cursor.close()
            conn.close()
            return jsonify({"error": "No member profile linked to this account."}), 400

        cursor.execute(
            "INSERT INTO payments (member_id,amount,payment_date,method,status,transaction_id,notes) "
            "VALUES (%s,%s,CURRENT_DATE,'online','pending',%s,%s) RETURNING payment_id",
            (member_id, float(amount), txn_id, data.get("notes") or None)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Member payment submitted: member={member_id} amount={amount} (id={new_id})")
        return jsonify({
            "message": "Payment submitted for verification.",
            "status": "success",
            "id": new_id
        }), 201
    except Exception as e:
        logger.error(f"member_add_payment: {e}")
        return jsonify({"error": "Could not submit payment."}), 500


@login_required
@role_required("admin")
def verify_payment(id):
    """Admin approves or rejects a pending Online payment."""
    data   = request.get_json(force=True, silent=True) or {}
    action = (data.get("action") or "").strip().lower()

    if action not in ("approve", "reject"):
        return jsonify({"error": "Action must be 'approve' or 'reject'."}), 400

    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM payments WHERE payment_id=%s", (id,))
        payment = cursor.fetchone()
        if not payment:
            cursor.close()
            conn.close()
            return jsonify({"error": "Payment not found."}), 404
        if payment["status"] != "pending":
            cursor.close()
            conn.close()
            return jsonify({"error": "Only pending payments can be verified."}), 400

        new_status = "paid" if action == "approve" else "rejected"
        cursor.execute("UPDATE payments SET status=%s WHERE payment_id=%s", (new_status, id))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Payment {id} verified: {new_status}")
        return jsonify({"message": f"Payment {new_status}.", "status": "success"})
    except Exception as e:
        logger.error(f"verify_payment {id}: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def update_payment(id):
    data   = request.get_json(force=True, silent=True) or {}
    mode   = (data.get("method") or data.get("payment_mode") or "cash").strip().lower()
    status = (data.get("status") or "paid").strip().lower()
    txn_id = (data.get("transaction_id") or "").strip()

    if mode not in PAYMENT_MODES:
        return jsonify({"error": "Payment mode must be Cash or Online."}), 400
    if status not in PAYMENT_STATUSES:
        return jsonify({"error": "Status must be Pending, Paid, or Rejected."}), 400
    if mode == "online" and not txn_id:
        return jsonify({"error": "Transaction ID is required for online payments."}), 400
    if mode == "cash":
        txn_id = ""

    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE payments SET member_id=%s,amount=%s,payment_date=%s,"
            "method=%s,status=%s,transaction_id=%s,notes=%s WHERE payment_id=%s",
            (data.get("member_id"),
             data.get("amount"),
             data.get("date") or None,
             mode,
             status,
             txn_id,
             data.get("notes") or None,
             id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Payment updated.", "status": "success"})
    except Exception as e:
        logger.error(f"update_payment {id}: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def delete_payment(id):
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM payments WHERE payment_id=%s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Payment deleted: id={id}")
        return jsonify({"message": "Payment deleted.", "status": "success"})
    except Exception as e:
        logger.error(f"delete_payment {id}: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  WORKOUTS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer", "member")
def get_workouts():
    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM workouts ORDER BY workout_id DESC")
        rows = [serialize_row(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"get_workouts: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def add_workout():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Workout name is required."}), 400

    exercises = data.get("exercises", [])
    if isinstance(exercises, list):
        exercises = ", ".join(exercises)

    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workouts (name,category,duration,difficulty,description,exercises,member_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (name,
             data.get("category") or "General",
             data.get("duration") or None,
             data.get("difficulty") or "beginner",
             data.get("description") or "",
             exercises,
             data.get("member_id") or None)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        logger.info(f"Workout added: {name} (id={new_id})")
        return jsonify({"message": "Workout created.", "status": "success", "id": new_id}), 201
    except Exception as e:
        logger.error(f"add_workout: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def update_workout(id):
    data = request.get_json(force=True, silent=True) or {}
    exercises = data.get("exercises", [])
    if isinstance(exercises, list):
        exercises = ", ".join(exercises)
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE workouts SET name=%s,category=%s,duration=%s,difficulty=%s,"
            "description=%s,exercises=%s,member_id=%s WHERE workout_id=%s",
            (data.get("name"),
             data.get("category") or "General",
             data.get("duration") or None,
             data.get("difficulty") or "beginner",
             data.get("description") or "",
             exercises,
             data.get("member_id") or None,
             id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Workout updated.", "status": "success"})
    except Exception as e:
        logger.error(f"update_workout {id}: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def delete_workout(id):
    try:
        conn   = db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workouts WHERE workout_id=%s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Workout deleted: id={id}")
        return jsonify({"message": "Workout deleted.", "status": "success"})
    except Exception as e:
        logger.error(f"delete_workout {id}: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer")
def get_stats():
    try:
        conn   = db()
        cursor = conn.cursor(dictionary=True)

        def val(sql):
            cursor.execute(sql)
            row = cursor.fetchone()
            return list(row.values())[0] if row else 0

        stats = {
            "total_members":   val("SELECT COUNT(*) FROM members"),
            "active_members":  val("SELECT COUNT(*) FROM members WHERE status='active'"),
            "total_trainers":  val("SELECT COUNT(*) FROM trainers"),
            "total_workouts":  val("SELECT COUNT(*) FROM workouts"),
            "monthly_revenue": float(val(
                "SELECT COALESCE(SUM(amount),0) FROM payments "
                "WHERE status='paid' AND payment_date >= DATE_TRUNC('month', CURRENT_DATE) "
                "AND payment_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'"
            )),
            "due_payments":    float(val(
                "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status IN ('due','pending')"
            )),
            "due_count":       val("SELECT COUNT(*) FROM payments WHERE status IN ('due','pending')"),
        }
        cursor.close()
        conn.close()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"get_stats: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  AI CHAT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def chat():
    data = request.get_json(force=True, silent=True) or {}
    msg  = (data.get("message") or "").lower().strip()
    if not msg:
        return jsonify({"reply": "Please type a message to get started!"})

    reply = None

    try:
        conn   = db()
        cursor = conn.cursor()

        def q(sql, params=()):
            try:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return row[0] if row else 0
            except Exception:
                return 0

        # ── Member queries ──
        if re.search(r"(how many|total|count).*(member)|member.*(count|total|how many)", msg):
            total  = q("SELECT COUNT(*) FROM members")
            active = q("SELECT COUNT(*) FROM members WHERE status='active'")
            reply  = "<strong>{}</strong> total members, <strong>{}</strong> currently active.".format(total, active)

        elif "active member" in msg:
            active = q("SELECT COUNT(*) FROM members WHERE status='active'")
            reply  = "There are <strong>{}</strong> active members right now.".format(active)

        # ── Payment queries ──
        elif re.search(r"(pending|due|unpaid).*(payment)|payment.*(pending|due)", msg):
            count  = q("SELECT COUNT(*) FROM payments WHERE status IN ('due','pending')")
            amount = q("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status IN ('due','pending')")
            reply  = "<strong>{}</strong> pending/due payments totalling <strong>₹{:,.0f}</strong>. <a href='payments.html' style='color:var(--accent)'>View →</a>".format(count, float(amount))

        elif re.search(r"revenue|income|earning|collection", msg):
            rev = q(
                "SELECT COALESCE(SUM(amount),0) FROM payments "
                "WHERE status='paid' AND MONTH(payment_date)=MONTH(NOW()) AND YEAR(payment_date)=YEAR(NOW())"
            )
            total = q("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'")
            reply = "This month: <strong>₹{:,.0f}</strong> collected. All-time total: <strong>₹{:,.0f}</strong>.".format(float(rev), float(total))

        # ── Trainer queries ──
        elif re.search(r"(how many|total|count).*(trainer)|trainer.*(count|total)", msg):
            total = q("SELECT COUNT(*) FROM trainers")
            reply = "You have <strong>{}</strong> trainers on your roster. <a href='trainers.html' style='color:var(--accent)'>View →</a>".format(total)

        elif "trainer" in msg:
            reply = "Manage your training staff on the <a href='trainers.html' style='color:var(--accent)'>Trainers</a> page."

        # ── Workout queries ──
        elif re.search(r"(how many|total|count).*(workout)|workout.*(count|total)", msg):
            total = q("SELECT COUNT(*) FROM workouts")
            reply = "There are <strong>{}</strong> workout programs available. <a href='workouts.html' style='color:var(--accent)'>View →</a>".format(total)

        elif "beginner" in msg:
            reply = ("🏋️ <strong>Beginner Plan (3 days/week):</strong><br>"
                     "Day 1: Squats 3×12, Push-ups 3×10, Plank 30s<br>"
                     "Day 3: Lunges 3×12, Dumbbell Rows 3×10, Crunches 3×20<br>"
                     "Day 5: Full Body Circuit — 20 min moderate pace<br>"
                     "Increase weight by 5% every week!")

        elif "intermediate" in msg:
            reply = ("💪 <strong>Intermediate Plan (4 days/week):</strong><br>"
                     "Push/Pull split — Bench, Squat, Deadlift as compounds.<br>"
                     "Add isolation work: curls, tricep dips, lateral raises.<br>"
                     "Progressive overload every 2 weeks.")

        elif "advanced" in msg:
            reply = ("🔥 <strong>Advanced Plan (5 days PPL):</strong><br>"
                     "Push / Pull / Legs split at 80–90% 1RM.<br>"
                     "3 weeks volume → 1 week deload. Periodised programming.")

        elif "workout" in msg:
            reply = "Browse all workout programs on the <a href='workouts.html' style='color:var(--accent)'>Workouts</a> page."

        # ── Business tips ──
        elif re.search(r"retain|retention|keep member", msg):
            reply = ("💡 <strong>Member retention tips:</strong><br>"
                     "• Send renewal reminders 7 days before expiry<br>"
                     "• Follow up with members inactive for 2+ weeks<br>"
                     "• Run monthly fitness challenges with rewards<br>"
                     "• Personalise workout plans for each member<br>"
                     "• Offer referral discounts")

        elif re.search(r"revenue.*increase|increase.*revenue|grow.*business|more.*member", msg):
            reply = ("📈 <strong>Growth strategies:</strong><br>"
                     "• Offer 3/6/12-month membership discounts<br>"
                     "• Launch personal training packages<br>"
                     "• Run referral programmes<br>"
                     "• Follow up on all due payments promptly<br>"
                     "• Add group fitness classes")

        # ── Navigation ──
        elif "dashboard" in msg:
            reply = "The <a href='dashboard.html' style='color:var(--accent)'>Dashboard</a> gives you a live overview of members, revenue, and activity."

        elif "payment" in msg:
            reply = "All billing records are on the <a href='payments.html' style='color:var(--accent)'>Payments</a> page."

        elif "member" in msg:
            reply = "Manage all member profiles on the <a href='members.html' style='color:var(--accent)'>Members</a> page."

        # ── Greetings ──
        elif re.search(r"\b(hi|hello|hey|helo|hii|namaste)\b", msg):
            user  = get_current_user() or {}
            name  = user.get("username", "there")
            reply = "👋 Hi <strong>{}</strong>! I'm your GymPro AI assistant. Ask me about members, revenue, workouts, trainers, or fitness tips.".format(name)

        elif re.search(r"help|what can you do|commands", msg):
            reply = ("I can help you with:<br>"
                     "📊 <strong>Live stats</strong> — members, revenue, due payments<br>"
                     "🏋️ <strong>Workout plans</strong> — beginner / intermediate / advanced<br>"
                     "💡 <strong>Business tips</strong> — retention, revenue growth<br>"
                     "🔗 <strong>Quick navigation</strong> — links to any page<br><br>"
                     "Just ask in plain English!")

        else:
            reply = ("I'm not sure about that. Try asking:<br>"
                     "<em>how many members, revenue this month, pending payments, "
                     "trainer count, beginner workout plan, retention tips</em><br>"
                     "Or type <strong>help</strong> to see everything I can do.")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"chat error: {e}")
        reply = "Sorry, I couldn't fetch live data right now. Please try again."

    return jsonify({"reply": reply, "status": "success"})


# ══════════════════════════════════════════════════════════════════════════════
#  MEMBERSHIP PLANS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer", "member")
def get_plans():
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM plans WHERE is_active=1 ORDER BY price ASC")
        rows = [serialize_row(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def add_plan():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Plan name is required."}), 400
    if not data.get("duration_days") or not data.get("price"):
        return jsonify({"error": "Duration and price are required."}), 400
    features = data.get("features", [])
    if isinstance(features, list):
        features = ",".join(features)
    try:
        conn = db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO plans (name,duration_days,price,description,features) VALUES (%s,%s,%s,%s,%s)",
            (name, int(data["duration_days"]), float(data["price"]),
             data.get("description",""), features)
        )
        conn.commit(); nid = cur.lastrowid
        cur.close(); conn.close()
        return jsonify({"message": "Plan created.", "status": "success", "id": nid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def update_plan(id):
    data = request.get_json(force=True, silent=True) or {}
    features = data.get("features", [])
    if isinstance(features, list):
        features = ",".join(features)
    try:
        conn = db(); cur = conn.cursor()
        cur.execute(
            "UPDATE plans SET name=%s,duration_days=%s,price=%s,description=%s,features=%s,is_active=%s WHERE plan_id=%s",
            (data.get("name"), int(data.get("duration_days",30)), float(data.get("price",0)),
             data.get("description",""), features, int(data.get("is_active",1)), id)
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "Plan updated.", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def delete_plan(id):
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE plans SET is_active=0 WHERE plan_id=%s", (id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "Plan deactivated.", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  MEMBERSHIPS (plan assignments to members)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer", "member")
def get_memberships():
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT ms.*, m.name AS member_name, m.phone AS member_phone,
                   p.name AS plan_name, p.duration_days, p.price AS plan_price,
                     (ms.end_date - CURRENT_DATE) AS days_remaining
            FROM memberships ms
            JOIN members m ON ms.member_id = m.member_id
            JOIN plans   p ON ms.plan_id   = p.plan_id
            ORDER BY ms.end_date ASC
        """)
        rows = [serialize_row(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def add_membership():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("member_id") or not data.get("plan_id"):
        return jsonify({"error": "member_id and plan_id are required."}), 400
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        # get plan duration
        cur.execute("SELECT * FROM plans WHERE plan_id=%s", (data["plan_id"],))
        plan = cur.fetchone()
        if not plan:
            return jsonify({"error": "Plan not found."}), 404

        start = data.get("start_date") or __import__('datetime').date.today().isoformat()
        from datetime import date, timedelta
        start_dt = date.fromisoformat(start)
        end_dt   = start_dt + timedelta(days=int(plan["duration_days"]))

        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO memberships (member_id,plan_id,start_date,end_date,status,paid_amount,payment_method,notes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (int(data["member_id"]), int(data["plan_id"]),
             start_dt.isoformat(), end_dt.isoformat(),
             "active",
             float(data.get("paid_amount", plan["price"])),
             data.get("payment_method","cash"),
             data.get("notes",""))
        )
        # update member status to active
        cur2.execute("UPDATE members SET status='active' WHERE member_id=%s", (data["member_id"],))
        conn.commit(); nid = cur2.lastrowid
        cur.close(); cur2.close(); conn.close()
        logger.info(f"Membership assigned: member={data['member_id']} plan={data['plan_id']}")
        return jsonify({"message": "Membership assigned.", "status": "success", "id": nid,
                        "end_date": end_dt.isoformat()}), 201
    except Exception as e:
        logger.error(f"add_membership: {e}")
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin")
def update_membership(id):
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = db(); cur = conn.cursor()
        cur.execute(
            "UPDATE memberships SET status=%s,paid_amount=%s,notes=%s WHERE membership_id=%s",
            (data.get("status","active"), data.get("paid_amount",0), data.get("notes",""), id)
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "Membership updated.", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer", "member")
def get_expiring_memberships():
    """Members expiring within next 7 days."""
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT ms.*, m.name AS member_name, m.phone AS member_phone,
                   p.name AS plan_name,
                                     (ms.end_date - CURRENT_DATE) AS days_remaining
            FROM memberships ms
            JOIN members m ON ms.member_id = m.member_id
            JOIN plans   p ON ms.plan_id   = p.plan_id
            WHERE ms.status='active'
                            AND ms.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
            ORDER BY ms.end_date ASC
        """)
        rows = [serialize_row(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer", "member")
def get_attendance():
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        date_filter = request.args.get("date")
        member_filter = request.args.get("member_id")

        sql = """
            SELECT a.*, m.name AS member_name, m.phone AS member_phone
            FROM attendance a
            JOIN members m ON a.member_id = m.member_id
            WHERE 1=1
        """
        params = []
        if date_filter:
            sql += " AND DATE(a.check_in) = %s"
            params.append(date_filter)
        if member_filter:
            sql += " AND a.member_id = %s"
            params.append(int(member_filter))
        sql += " ORDER BY a.check_in DESC LIMIT 200"

        cur.execute(sql, params)
        rows = [serialize_row(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def mark_attendance():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("member_id"):
        return jsonify({"error": "member_id is required."}), 400
    user = get_current_user()
    try:
        conn = db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO attendance (member_id,check_in,notes,marked_by) VALUES (%s,%s,%s,%s)",
            (int(data["member_id"]),
             data.get("check_in") or __import__('datetime').datetime.now().isoformat(),
             data.get("notes",""),
             user.get("username","admin") if user else "admin")
        )
        conn.commit(); nid = cur.lastrowid
        cur.close(); conn.close()
        return jsonify({"message": "Attendance marked.", "status": "success", "id": nid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def checkout_attendance(id):
    try:
        conn = db(); cur = conn.cursor()
        cur.execute(
            "UPDATE attendance SET check_out=%s WHERE attendance_id=%s AND check_out IS NULL",
            (__import__('datetime').datetime.now().isoformat(), id)
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "Checked out.", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def get_today_attendance():
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.*, m.name AS member_name
            FROM attendance a
            JOIN members m ON a.member_id = m.member_id
            WHERE DATE(a.check_in) = CURDATE()
            ORDER BY a.check_in DESC
        """)
        rows = [serialize_row(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer")
def get_notifications():
    try:
        conn = db(); cur = conn.cursor(dictionary=True)
        # auto-generate expiry notifications
        _generate_expiry_notifications(conn)
        cur.execute("""
            SELECT n.*, m.name AS member_name
            FROM notifications n
            LEFT JOIN members m ON n.member_id = m.member_id
            ORDER BY n.created_at DESC LIMIT 50
        """)
        rows = [serialize_row(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def mark_notification_read(id):
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE notifications SET is_read=1 WHERE notif_id=%s", (id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "Marked as read.", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
@role_required("admin", "trainer")
def mark_all_notifications_read():
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE notifications SET is_read=1")
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "All marked as read.", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _generate_expiry_notifications(conn):
    """Auto-create alerts for memberships expiring within 7 days."""
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT ms.membership_id, ms.member_id, m.name,
                   p.name AS plan_name, ms.end_date,
                   DATEDIFF(ms.end_date, CURDATE()) AS days_left
            FROM memberships ms
            JOIN members m ON ms.member_id = m.member_id
            JOIN plans   p ON ms.plan_id   = p.plan_id
            WHERE ms.status='active'
              AND ms.end_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        """)
        expiring = cur.fetchall()
        for e in expiring:
            # don't duplicate — check if notification for this membership already exists today
            cur.execute("""
                SELECT notif_id FROM notifications
                WHERE member_id=%s AND type='expiry'
                  AND DATE(created_at)=CURDATE()
            """, (e["member_id"],))
            if not cur.fetchone():
                days = e["days_left"]
                if days == 0:
                    title = f"⚠️ {e['name']}'s membership expires TODAY!"
                elif days < 0:
                    title = f"❌ {e['name']}'s membership has expired"
                else:
                    title = f"⏰ {e['name']}'s membership expires in {days} day(s)"
                cur.execute(
                    "INSERT INTO notifications (type,title,message,member_id) VALUES (%s,%s,%s,%s)",
                    ("expiry", title,
                     f"Plan: {e['plan_name']} | Expires: {e['end_date']}", e["member_id"])
                )
        conn.commit()
        cur.close()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required("admin", "trainer")
def get_report():
    report_type = request.args.get("type", "monthly")
    try:
        conn = db(); cur = conn.cursor(dictionary=True)

        if report_type == "monthly":
            cur.execute("""
                SELECT
                    DATE_FORMAT(payment_date,'%Y-%m') AS month,
                    COUNT(*) AS transactions,
                    SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) AS collected,
                    SUM(CASE WHEN status IN ('due','pending') THEN amount ELSE 0 END) AS pending
                FROM payments
                GROUP BY DATE_FORMAT(payment_date,'%Y-%m')
                ORDER BY month DESC LIMIT 12
            """)
            data = [serialize_row(r) for r in cur.fetchall()]

        elif report_type == "members":
            cur.execute("""
                SELECT
                    DATE_FORMAT(join_date,'%Y-%m') AS month,
                    COUNT(*) AS new_members,
                    SUM(CASE WHEN status='active'   THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN status='inactive' THEN 1 ELSE 0 END) AS inactive
                FROM members
                GROUP BY DATE_FORMAT(join_date,'%Y-%m')
                ORDER BY month DESC LIMIT 12
            """)
            data = [serialize_row(r) for r in cur.fetchall()]

        elif report_type == "attendance":
            cur.execute("""
                SELECT
                    DATE(check_in) AS date,
                    COUNT(*) AS total_visits,
                    COUNT(DISTINCT member_id) AS unique_members
                FROM attendance
                GROUP BY DATE(check_in)
                ORDER BY date DESC LIMIT 30
            """)
            data = [serialize_row(r) for r in cur.fetchall()]

        elif report_type == "plans":
            cur.execute("""
                SELECT
                    p.name AS plan_name, p.price,
                    COUNT(ms.membership_id) AS total_sold,
                    SUM(ms.paid_amount) AS total_revenue,
                    SUM(CASE WHEN ms.status='active' THEN 1 ELSE 0 END) AS currently_active
                FROM plans p
                LEFT JOIN memberships ms ON p.plan_id = ms.plan_id
                GROUP BY p.plan_id, p.name, p.price
                ORDER BY total_sold DESC
            """)
            data = [serialize_row(r) for r in cur.fetchall()]

        else:
            data = []

        cur.close(); conn.close()
        return jsonify({"type": report_type, "data": data})
    except Exception as e:
        logger.error(f"get_report ({report_type}): {e}")
        return jsonify({"error": str(e)}), 500

