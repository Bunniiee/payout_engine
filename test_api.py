import requests
import uuid
import sys

BASE = "http://localhost:8000/api/v1"
MERCHANT_ID = "000a40db-ea62-4ce6-9d26-6d72b92b610f"
IDEM_KEY = str(uuid.uuid4())

ok = True

def check(label, cond, got=""):
    global ok
    status = "PASS" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"  [{status}] {label}" + (f" — got: {got}" if not cond else ""))

print("=== Test 1: GET /merchants/ ===")
r = requests.get(f"{BASE}/merchants/")
check("HTTP 200", r.status_code == 200, r.status_code)
data = r.json()
check("3 merchants", len(data) == 3, len(data))
arjun = next(m for m in data if m["name"] == "Arjun Mehta")
check("Arjun balance 630000p", arjun["available_balance_paise"] == 630000, arjun["available_balance_paise"])
check("Arjun held 0", arjun["held_balance_paise"] == 0, arjun["held_balance_paise"])

print("\n=== Test 2: GET /merchants/me/ ===")
r = requests.get(f"{BASE}/merchants/me/", headers={"X-Merchant-ID": MERCHANT_ID})
check("HTTP 200", r.status_code == 200, r.status_code)
me = r.json()
check("correct merchant", me["id"] == MERCHANT_ID, me["id"])
check("held balance 0", me["held_balance_paise"] == 0, me["held_balance_paise"])

print("\n=== Test 3: POST /payouts/ (create) ===")
payout_headers = {
    "X-Merchant-ID": MERCHANT_ID,
    "Idempotency-Key": IDEM_KEY,
    "Content-Type": "application/json",
}
r = requests.post(f"{BASE}/payouts/", headers=payout_headers, json={"amount_paise": 50000, "bank_account_id": "HDFC_ACC_001"})
check("HTTP 201", r.status_code == 201, r.status_code)
payout = r.json()
payout_id = payout["id"]
check("status pending", payout["status"] == "pending", payout["status"])
check("amount 50000", payout["amount_paise"] == 50000, payout["amount_paise"])
print(f"  Payout ID: {payout_id}")

print("\n=== Test 4: POST same key (idempotency) ===")
r2 = requests.post(f"{BASE}/payouts/", headers=payout_headers, json={"amount_paise": 50000, "bank_account_id": "HDFC_ACC_001"})
check("HTTP 200 (existing)", r2.status_code == 200, r2.status_code)
payout2 = r2.json()
check("same payout ID", payout2["id"] == payout_id, payout2["id"])

print("\n=== Test 5: Balance after hold ===")
r = requests.get(f"{BASE}/merchants/me/", headers={"X-Merchant-ID": MERCHANT_ID})
me2 = r.json()
check("available 580000 (630000 - 50000)", me2["available_balance_paise"] == 580000, me2["available_balance_paise"])
check("held 50000", me2["held_balance_paise"] == 50000, me2["held_balance_paise"])

print("\n=== Test 6: Insufficient funds (HTTP 422) ===")
big_headers = {
    "X-Merchant-ID": MERCHANT_ID,
    "Idempotency-Key": str(uuid.uuid4()),
    "Content-Type": "application/json",
}
r = requests.post(f"{BASE}/payouts/", headers=big_headers, json={"amount_paise": 9999999, "bank_account_id": "HDFC_ACC_001"})
check("HTTP 422", r.status_code == 422, r.status_code)

print("\n=== Test 7: GET /ledger/ ===")
r = requests.get(f"{BASE}/ledger/", headers={"X-Merchant-ID": MERCHANT_ID})
check("HTTP 200", r.status_code == 200, r.status_code)
entries = r.json()["results"]
types = [e["entry_type"] for e in entries]
check("has HOLD entry", "HOLD" in types, types)
check("has CREDIT entries", "CREDIT" in types, types)

print("\n=== Test 8: GET /payouts/ ===")
r = requests.get(f"{BASE}/payouts/", headers={"X-Merchant-ID": MERCHANT_ID})
check("HTTP 200", r.status_code == 200, r.status_code)
payouts = r.json()["results"]
check("1 payout", len(payouts) == 1, len(payouts))

print("\n=== Test 9: Missing Idempotency-Key ===")
r = requests.post(f"{BASE}/payouts/", headers={"X-Merchant-ID": MERCHANT_ID, "Content-Type": "application/json"}, json={"amount_paise": 1000, "bank_account_id": "HDFC"})
check("HTTP 400", r.status_code == 400, r.status_code)

print("\n=== Test 10: Invalid Idempotency-Key ===")
bad_headers = {"X-Merchant-ID": MERCHANT_ID, "Idempotency-Key": "not-a-uuid", "Content-Type": "application/json"}
r = requests.post(f"{BASE}/payouts/", headers=bad_headers, json={"amount_paise": 1000, "bank_account_id": "HDFC"})
check("HTTP 400", r.status_code == 400, r.status_code)

print()
if ok:
    print("All tests PASSED!")
else:
    print("Some tests FAILED!")
    sys.exit(1)
