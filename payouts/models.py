import uuid
from django.db import models
from .exceptions import InvalidTransition

ALLOWED_TRANSITIONS = {
    'pending':    ['processing'],
    'processing': ['completed', 'failed'],
}


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Payout(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name='payouts')
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    idempotency_key = models.CharField(max_length=64)
    attempts = models.PositiveIntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['merchant', 'idempotency_key'],
                name='unique_idempotency_per_merchant',
            )
        ]

    def transition_to(self, new_status):
        allowed = ALLOWED_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidTransition(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed from '{self.status}': {allowed}"
            )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f"Payout({self.id}, {self.status}, {self.amount_paise}p)"


class LedgerEntry(models.Model):
    CREDIT = 'CREDIT'
    HOLD = 'HOLD'
    HOLD_RELEASE = 'HOLD_RELEASE'

    ENTRY_TYPES = [
        (CREDIT, 'Credit'),
        (HOLD, 'Hold'),
        (HOLD_RELEASE, 'Hold Release'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name='ledger_entries')
    amount_paise = models.BigIntegerField()
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    payout = models.ForeignKey(
        Payout, null=True, blank=True, on_delete=models.PROTECT, related_name='ledger_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LedgerEntry({self.entry_type}, {self.amount_paise}p)"
