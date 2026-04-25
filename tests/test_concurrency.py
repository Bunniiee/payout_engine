import threading
import uuid

from django.test import TransactionTestCase

from payouts.models import Merchant, LedgerEntry, Payout
from payouts.services import create_payout, get_available_balance
from payouts.exceptions import InsufficientFunds


def _seed_merchant(email, balance_paise):
    merchant = Merchant.objects.create(name='Test Merchant', email=email)
    LedgerEntry.objects.create(
        merchant=merchant,
        amount_paise=balance_paise,
        entry_type=LedgerEntry.CREDIT,
    )
    return merchant


class ConcurrentPayoutTest(TransactionTestCase):
    def test_concurrent_payouts_only_one_succeeds(self):
        merchant = _seed_merchant('concurrent@test.com', 10000)

        results = []
        errors = []

        def attempt():
            try:
                payout, created = create_payout(
                    merchant_id=str(merchant.id),
                    amount_paise=6000,
                    bank_account_id='HDFC_001',
                    idempotency_key=str(uuid.uuid4()),
                )
                results.append('success')
            except InsufficientFunds:
                results.append('rejected')
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Unexpected errors: {errors}")
        self.assertEqual(results.count('success'), 1, f"Expected exactly 1 success, got: {results}")
        self.assertEqual(results.count('rejected'), 1, f"Expected exactly 1 rejection, got: {results}")

        merchant.refresh_from_db()
        balance = get_available_balance(merchant)
        self.assertEqual(balance, 4000, f"Expected 4000 paise remaining, got: {balance}")

        payout_count = Payout.objects.filter(merchant=merchant).count()
        self.assertEqual(payout_count, 1, f"Expected exactly 1 payout created, got: {payout_count}")
