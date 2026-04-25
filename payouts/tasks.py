import random
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Payout, LedgerEntry


@shared_task(name='payouts.tasks.process_payout')
def process_payout(payout_id):
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(id=payout_id)
        except Payout.DoesNotExist:
            return

        if payout.status != Payout.PENDING:
            return

        payout.transition_to(Payout.PROCESSING)
        payout.attempts += 1
        payout.processing_started_at = timezone.now()
        payout.save(update_fields=['attempts', 'processing_started_at', 'updated_at'])

    r = random.random()

    if r < 0.70:
        with transaction.atomic():
            payout.refresh_from_db()
            payout.transition_to(Payout.COMPLETED)
    elif r < 0.90:
        with transaction.atomic():
            payout.refresh_from_db()
            payout.transition_to(Payout.FAILED)
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                amount_paise=payout.amount_paise,
                entry_type=LedgerEntry.HOLD_RELEASE,
                payout=payout,
            )


@shared_task(name='payouts.tasks.retry_stuck_payouts')
def retry_stuck_payouts():
    cutoff = timezone.now() - timedelta(seconds=30)

    with transaction.atomic():
        stuck_payouts = list(
            Payout.objects.select_for_update(skip_locked=True).filter(
                status=Payout.PROCESSING,
                processing_started_at__lt=cutoff,
            )
        )

        for payout in stuck_payouts:
            if payout.attempts < 3:
                payout.status = Payout.PENDING
                payout.processing_started_at = None
                payout.save(update_fields=['status', 'processing_started_at', 'updated_at'])
                process_payout.delay(str(payout.id))
            else:
                payout.transition_to(Payout.FAILED)
                LedgerEntry.objects.create(
                    merchant=payout.merchant,
                    amount_paise=payout.amount_paise,
                    entry_type=LedgerEntry.HOLD_RELEASE,
                    payout=payout,
                )
