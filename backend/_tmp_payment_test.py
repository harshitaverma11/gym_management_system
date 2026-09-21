import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5000"
ADMIN_HEADER = json.dumps({"username": "admin", "role": "admin", "user_id": 1})


def call(method, path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(BASE + path, data=data, headers=req_headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        body_text = e.read()
        try:
            return e.code, json.loads(body_text or b"{}")
        except Exception:
            return e.code, {"raw": body_text.decode(errors="replace")}


results = []

username = "pay_test_member_20260920_2"
status, body = call("POST", "/signup", {
    "username": username, "password": "test123456",
    "full_name": "Pay Test Member", "phone": "9991110000", "age": 30,
    "gender": "M", "address": "Test Address", "city": "Testville",
    "emergency_contact": "9991110001",
})
results.append(("signup", status))
user_id = body.get("user", {}).get("user_id")

status, members = call("GET", "/members", headers={"X-User": ADMIN_HEADER})
results.append(("get_members(admin)", status))
member_row = next((m for m in members if m.get("user_id") == user_id), None)
member_id = member_row.get("member_id") if member_row else None

status, _ = call("POST", "/login", {"username": username, "password": "test123456", "role": "member"})
results.append(("member_login", status))

member_header = json.dumps({"username": username, "role": "member", "user_id": user_id})

status, body = call("POST", "/payments/member", {"amount": 1500, "transaction_id": "UPI123456789"}, {"X-User": member_header})
results.append(("member_add_payment", status))
payment_id = body.get("id")

status, own_payments = call("GET", "/payments", headers={"X-User": member_header})
results.append(("member_get_payments(count=%d)" % len(own_payments), status))
match = next((p for p in own_payments if p.get("payment_id") == payment_id), None)
results.append(("member_payment_shape_ok", bool(match and match.get("status") == "pending" and match.get("method") == "online" and match.get("transaction_id") == "UPI123456789" and float(match.get("amount")) == 1500)))
results.append(("member_sees_only_own(count=%d)" % len(own_payments), all(p.get("member_id") == member_id for p in own_payments)))

status, admin_payments = call("GET", "/payments", headers={"X-User": ADMIN_HEADER})
results.append(("admin_get_payments(count=%d)" % len(admin_payments), status))
admin_match = next((p for p in admin_payments if p.get("payment_id") == payment_id), None)
results.append(("admin_sees_pending_with_name", bool(admin_match and admin_match.get("member_name"))))

status, _ = call("POST", f"/payments/{payment_id}/verify", {"action": "approve"}, {"X-User": ADMIN_HEADER})
results.append(("verify_approve", status))

status, own_payments2 = call("GET", "/payments", headers={"X-User": member_header})
match2 = next((p for p in own_payments2 if p.get("payment_id") == payment_id), None)
results.append(("after_approve_status_paid", match2.get("status") if match2 else None))

status, _ = call("POST", "/payments", {"member_id": member_id, "amount": 500, "method": "cash", "status": "paid"}, {"X-User": ADMIN_HEADER})
results.append(("admin_cash_payment_no_txn", status))

status, _ = call("POST", "/payments", {"member_id": member_id, "amount": 700, "method": "online", "status": "pending"}, {"X-User": ADMIN_HEADER})
results.append(("admin_online_payment_missing_txn(expect 400)", status))

status, _ = call("POST", "/payments", {"member_id": member_id, "amount": 100, "method": "cash", "status": "paid"}, {"X-User": member_header})
results.append(("member_calls_admin_add_payment(expect 403)", status))

for name, value in results:
    print(name, "=>", value)
