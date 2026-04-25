# EXPLAINER.md — Playto Payout Engine

---

## 1. The Ledger — Balance Calculation

**The query:**

```python
# payouts/services.py
from django.db.models import Sum

def get_available_balance(merchant):
    result = LedgerEntry.objects.filter(
        merchant=merchant
    ).aggregate(total=Sum('amount_paise'))
    return result['total'] or 0
```

This is the **entire balance engine** — one `SUM` query. No stored balance column exists on `Merchant`.

**Why this model:**

All money movements are signed integers in a single `LedgerEntry` table:

| entry_type | amount_paise sign | When |
|---|---|---|
| `CREDIT` | positive | Customer pays merchant (seeded) |
| `HOLD` | negative | Merchant requests payout — funds reserved |
| `HOLD_RELEASE` | positive | Payout failed — funds returned |

`SUM(amount_paise)` across all entries for a merchant gives the exact available balance at any point in time. No Python arithmetic on individual rows. No risk of stored balance drifting from ledger reality.

On payout success, the `HOLD` entry stands as the permanent debit — no extra entry needed. On failure, a `HOLD_RELEASE` entry exactly cancels the `HOLD`.

---

## 2. The Lock — Preventing Concurrent Overdraft

**The exact code:**

```python
# payouts/services.py
def create_payout(merchant_id, amount_paise, bank_account_id, idempotency_key):
    with transaction.atomic():
        # Acquire exclusive row-level lock on the merchant row.
        # All concurrent payout requests for this merchant queue here.
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)

        # Balance is computed INSIDE the lock — safe from concurrent reads.
        available = get_available_balance(merchant)

        if available < amount_paise:
            raise InsufficientFunds(...)

        # This block is serialized — no two transactions can reach here
        # simultaneously for the same merchant.
        payout = Payout.objects.create(...)
        LedgerEntry.objects.create(amount_paise=-amount_paise, entry_type='HOLD', ...)
        return payout, True
    # Lock released when transaction commits.
```

**Database primitive:** PostgreSQL `SELECT ... FOR UPDATE` — an exclusive row-level lock on the `merchants` row.

**Why not Python-level locks:**

Django runs multiple gunicorn worker processes. `threading.Lock()` only works within a single process. A `Lock` in worker process A is invisible to worker process B. Under load, both workers would pass the balance check independently and create an overdraft.

`SELECT FOR UPDATE` is enforced at the PostgreSQL level — it works across all processes, servers, and workers. When request B tries to lock the merchant row, PostgreSQL blocks it until request A's transaction commits. At that point, B reads the updated balance (which now has A's HOLD deducted) and correctly fails with insufficient funds.

---

## 3. The Idempotency — Guaranteed Exactly-Once Creation

**How the system recognises a seen key:**

The `Payout` model has a database-level unique constraint:

```python
# payouts/models.py
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['merchant', 'idempotency_key'],
            name='unique_idempotency_per_merchant',
        )
    ]
```

The service uses a try/except pattern against this constraint:

```python
# payouts/services.py
try:
    payout = Payout.objects.create(idempotency_key=key, ...)
    LedgerEntry.objects.create(HOLD, -amount_paise)
    return payout, True          # created=True → 201
except IntegrityError:
    payout = Payout.objects.get(merchant=merchant, idempotency_key=key)
    return payout, False         # created=False → 200
```

**What happens when the first request is still in flight:**

If request A is inside `transaction.atomic()` and request B arrives with the same key:

1. B reaches `Payout.objects.create(...)` — PostgreSQL evaluates the unique constraint.
2. The constraint check sees A's row (even though A hasn't committed yet, the INSERT intent is visible at the lock level).
3. B gets `IntegrityError` and falls back to `Payout.objects.get(...)` — which waits for A's transaction to commit, then returns A's payout.

**Why not a pre-check (`if Payout.objects.filter(key=key).exists(): return`):**

```
T=0: A checks → not found
T=0: B checks → not found   ← same snapshot, gap exists
T=1: A creates
T=1: B creates → DUPLICATE  ← pre-check didn't help
```

The unique constraint makes exactly one `INSERT` succeed at the database level. The race is impossible.

**Key scoping:** The constraint is on `(merchant, idempotency_key)` — not just the key alone. Merchant A's key `abc` and Merchant B's key `abc` are independent.

**Key expiry (24h):** On lookup, the service checks `created_at >= now - 24h`. Keys older than 24 hours are treated as new requests.

---

## 4. The State Machine — Blocking Illegal Transitions

**The code:**

```python
# payouts/models.py
ALLOWED_TRANSITIONS = {
    'pending':    ['processing'],
    'processing': ['completed', 'failed'],
    # 'completed' and 'failed' have no entries → no transitions allowed
}

def transition_to(self, new_status):
    allowed = ALLOWED_TRANSITIONS.get(self.status, [])
    if new_status not in allowed:
        raise InvalidTransition(
            f"Cannot transition from '{self.status}' to '{new_status}'. "
            f"Allowed from '{self.status}': {allowed}"
        )
    self.status = new_status
    self.save(update_fields=['status', 'updated_at'])
```

`failed → completed` is blocked because `ALLOWED_TRANSITIONS['failed']` doesn't exist — `.get()` returns `[]`. `'completed'` is not in `[]` → `InvalidTransition` is raised.

`completed → pending` is blocked for the same reason.

`transition_to()` is the **only** way to change payout status. No view, task, or serializer sets `payout.status = ...` directly. The one exception is `retry_stuck_payouts`, which resets `processing → pending` directly — this is a deliberate retry reset, not a standard lifecycle transition, and it is isolated to that single function with a comment explaining why.

---

## 5. The AI Audit — Where the Machine Got It Wrong

**What AI generated:**

When I asked for the idempotency implementation, the initial suggestion was:

```python
# What AI wrote
def create_payout(merchant_id, amount_paise, bank_account_id, idempotency_key):
    # Check if key already exists
    existing = Payout.objects.filter(
        merchant_id=merchant_id,
        idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing, False

    with transaction.atomic():
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)
        available = get_available_balance(merchant)
        if available < amount_paise:
            raise InsufficientFunds()
        payout = Payout.objects.create(...)
        LedgerEntry.objects.create(...)
        return payout, True
```

**What I caught:**

The existence check `Payout.objects.filter(...).first()` is **outside** the `transaction.atomic()` block. This creates a race window:

```
T=0: Request A — filter() → not found
T=0: Request B — filter() → not found  (same DB snapshot)
T=1: A enters atomic, creates payout
T=1: B enters atomic, creates payout → IntegrityError uncaught → 500 error
```

Two problems:
1. The pre-check race means both requests see "not found" simultaneously.
2. When B hits `IntegrityError` inside the atomic block, there's no handler — it crashes instead of returning the existing payout.

**What I replaced it with:**

```python
def create_payout(merchant_id, amount_paise, bank_account_id, idempotency_key):
    expiry_cutoff = timezone.now() - timedelta(hours=24)

    with transaction.atomic():
        # Lock acquired FIRST. Existence check is inside the lock.
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)

        existing = Payout.objects.filter(
            merchant=merchant,
            idempotency_key=idempotency_key,
            created_at__gte=expiry_cutoff,
        ).first()
        if existing:
            return existing, False

        available = get_available_balance(merchant)
        if available < amount_paise:
            raise InsufficientFunds(...)

        try:
            payout = Payout.objects.create(...)
            LedgerEntry.objects.create(...)
            return payout, True
        except IntegrityError:
            # Safety net: concurrent request with same key
            payout = Payout.objects.get(
                merchant=merchant,
                idempotency_key=idempotency_key,
            )
            return payout, False
```

The key corrections:
1. The existence check is **inside** `transaction.atomic()` after the `select_for_update` lock — so no two requests for the same merchant can run the check simultaneously.
2. The `IntegrityError` is **caught** as a fallback — even if two requests somehow race through (e.g., different merchant IDs), the DB constraint catches it and we return gracefully.
3. The expiry check (`created_at__gte`) is applied to honour the 24-hour TTL for idempotency keys.
