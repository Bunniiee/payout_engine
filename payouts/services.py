from datetime import timedelta

from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.utils import timezone

from .models import Merchant, Payout, LedgerEntry
from .exceptions import InsufficientFunds

IDEMPOTENCY_TTL_HOURS = 24


def get_available_balance(merchant):
    result = LedgerEntry.objects.filter(
        merchant=merchant
    ).aggregate(total=Sum('amount_paise'))
    return result['total'] or 0


def get_held_balance(merchant):
    result = Payout.objects.filter(
        merchant=merchant,
        status__in=[Payout.PENDING, Payout.PROCESSING],
    ).aggregate(total=Sum('amount_paise'))
    return result['total'] or 0


def create_payout(merchant_id, amount_paise, bank_account_id, idempotency_key):
    expiry_cutoff = timezone.now() - timedelta(hours=IDEMPOTENCY_TTL_HOURS)

    with transaction.atomic():
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
            raise InsufficientFunds(
                f"Available balance {available} paise is less than requested {amount_paise} paise"
            )

        try:
            payout = Payout.objects.create(
                merchant=merchant,
                amount_paise=amount_paise,
                bank_account_id=bank_account_id,
                idempotency_key=idempotency_key,
                status=Payout.PENDING,
            )
            LedgerEntry.objects.create(
                merchant=merchant,
                amount_paise=-amount_paise,
                entry_type=LedgerEntry.HOLD,
                payout=payout,
            )
            return payout, True
        except IntegrityError:
            payout = Payout.objects.get(
                merchant=merchant,
                idempotency_key=idempotency_key,
            )
            return payout, False
