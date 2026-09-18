"""
GymPro — app.py
Production-ready Flask application entry point.
"""
import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Load environment variables ────────────────────────────────────────────────
try:
    from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
    load_dotenv()
except ImportError:
    pass

# ── Ensure tables exist on startup ───────────────────────────────────────────
import create_users_table
import create_workouts_table
create_users_table.ensure_users_table()

# ── Import routes ─────────────────────────────────────────────────────────────
import routes

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "gympro_dev_secret_2024_change_in_production")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── CORS ──────────────────────────────────────────────────────────────────────
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500,http://localhost,http://127.0.0.1,null"
)
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

CORS(app,
     supports_credentials=True,
     allow_headers=["Content-Type", "X-User", "Authorization", "Accept"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     origins=allowed_origins)

# ── Session / Cookie config ───────────────────────────────────────────────────
is_production = os.getenv("FLASK_ENV") == "production"
app.config.update(
    SESSION_COOKIE_SAMESITE = "None",
    SESSION_COOKIE_SECURE   = is_production,  # True in production (HTTPS required)
    SESSION_COOKIE_HTTPONLY = True,
    SESSION_COOKIE_PATH     = "/",
    PERMANENT_SESSION_LIFETIME = 86400,  # 24 hours
)

# ── Security headers (applied to every response) ─────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]         = "SAMEORIGIN"
    response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
    return response

# ── Global error handlers ─────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "status": 405}), 405

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({"error": "Internal server error", "status": 500}), 500

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "message": "GymPro API Running",
        "status":  "success",
        "version": "2.0"
    })

@app.route("/health")
def health():
    from database import test_connection
    db_ok = test_connection()
    return jsonify({
        "status":   "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "api":      "running"
    }), 200 if db_ok else 503

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/login",    "login",    routes.login,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/logout",   "logout",   routes.logout,   methods=["POST",   "OPTIONS"])
app.add_url_rule("/add_user", "add_user", routes.add_user, methods=["POST",   "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  MEMBER ROUTES
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/members",               "get_members",          routes.get_members,    methods=["GET",    "OPTIONS"])
app.add_url_rule("/members",               "add_member",           routes.add_member,     methods=["POST",   "OPTIONS"])
app.add_url_rule("/members/<int:id>",      "update_member",        routes.update_member,  methods=["PUT",    "OPTIONS"])
app.add_url_rule("/members/<int:id>",      "delete_member",        routes.delete_member,  methods=["DELETE", "OPTIONS"])
# Legacy aliases
app.add_url_rule("/add_member",            "add_member_l",         routes.add_member,     methods=["POST",   "OPTIONS"])
app.add_url_rule("/update_member/<int:id>","update_member_l",      routes.update_member,  methods=["PUT",    "OPTIONS"])
app.add_url_rule("/delete_member/<int:id>","delete_member_l",      routes.delete_member,  methods=["DELETE", "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  TRAINER ROUTES
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/trainers",              "get_trainers",         routes.get_trainers,   methods=["GET",    "OPTIONS"])
app.add_url_rule("/trainers",              "add_trainer",          routes.add_trainer,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/trainers/<int:id>",     "update_trainer",       routes.update_trainer, methods=["PUT",    "OPTIONS"])
app.add_url_rule("/trainers/<int:id>",     "delete_trainer",       routes.delete_trainer, methods=["DELETE", "OPTIONS"])
app.add_url_rule("/add_trainer",           "add_trainer_l",        routes.add_trainer,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/delete_trainer/<int:id>","delete_trainer_l",    routes.delete_trainer, methods=["DELETE", "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  PAYMENT ROUTES
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/payments",              "get_payments",         routes.get_payments,   methods=["GET",    "OPTIONS"])
app.add_url_rule("/payments",              "add_payment",          routes.add_payment,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/payments/<int:id>",     "update_payment",       routes.update_payment, methods=["PUT",    "OPTIONS"])
app.add_url_rule("/payments/<int:id>",     "delete_payment",       routes.delete_payment, methods=["DELETE", "OPTIONS"])
app.add_url_rule("/add_payment",           "add_payment_l",        routes.add_payment,    methods=["POST",   "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  WORKOUT ROUTES
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/workouts",              "get_workouts",         routes.get_workouts,   methods=["GET",    "OPTIONS"])
app.add_url_rule("/workouts",              "add_workout",          routes.add_workout,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/workouts/<int:id>",     "update_workout",       routes.update_workout, methods=["PUT",    "OPTIONS"])
app.add_url_rule("/workouts/<int:id>",     "delete_workout",       routes.delete_workout, methods=["DELETE", "OPTIONS"])
app.add_url_rule("/add_workout",           "add_workout_l",        routes.add_workout,    methods=["POST",   "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  UTILITY ROUTES
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/chat",  "chat",  routes.chat,      methods=["POST", "OPTIONS"])
app.add_url_rule("/stats", "stats", routes.get_stats, methods=["GET",  "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  PLANS
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/plans",          "get_plans",   routes.get_plans,   methods=["GET",    "OPTIONS"])
app.add_url_rule("/plans",          "add_plan",    routes.add_plan,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/plans/<int:id>", "update_plan", routes.update_plan, methods=["PUT",    "OPTIONS"])
app.add_url_rule("/plans/<int:id>", "delete_plan", routes.delete_plan, methods=["DELETE", "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  MEMBERSHIPS
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/memberships",            "get_memberships",    routes.get_memberships,    methods=["GET",    "OPTIONS"])
app.add_url_rule("/memberships",            "add_membership",     routes.add_membership,     methods=["POST",   "OPTIONS"])
app.add_url_rule("/memberships/<int:id>",   "update_membership",  routes.update_membership,  methods=["PUT",    "OPTIONS"])
app.add_url_rule("/memberships/expiring",   "expiring",           routes.get_expiring_memberships, methods=["GET","OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/attendance",             "get_attendance",     routes.get_attendance,     methods=["GET",    "OPTIONS"])
app.add_url_rule("/attendance",             "mark_attendance",    routes.mark_attendance,    methods=["POST",   "OPTIONS"])
app.add_url_rule("/attendance/<int:id>/checkout", "checkout",     routes.checkout_attendance,methods=["PUT",    "OPTIONS"])
app.add_url_rule("/attendance/today",       "today_attendance",   routes.get_today_attendance,methods=["GET",   "OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/notifications",             "get_notifications",      routes.get_notifications,      methods=["GET",  "OPTIONS"])
app.add_url_rule("/notifications/<int:id>/read","mark_read",             routes.mark_notification_read, methods=["PUT",  "OPTIONS"])
app.add_url_rule("/notifications/read-all",    "mark_all_read",          routes.mark_all_notifications_read, methods=["PUT","OPTIONS"])

# ══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ══════════════════════════════════════════════════════════════════════════════
app.add_url_rule("/reports", "get_report", routes.get_report, methods=["GET", "OPTIONS"])

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    port  = int(os.getenv("PORT", 5000))
    host  = "0.0.0.0" if not debug else "127.0.0.1"
    logger.info(f"Starting GymPro on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)
