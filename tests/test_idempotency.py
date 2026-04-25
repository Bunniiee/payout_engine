import uuid

from django.test import TransactionTestCase

from payouts.models import Merchant, LedgerEntry, Payout
from payouts.services import create_payout, get_available_balance


def _seed_merchant(email, balance_paise):
    merchant = Merchant.objects.create(name='Test Merchant', email=email)
    LedgerEntry.objects.create(
        merchant=merchant,
        amount_paise=balance_paise,
        entry_type=LedgerEntry.CREDIT,
    )
    return merchant


class IdempotencyTest(TransactionTestCase):
    def test_same_key_returns_same_payout(self):
        merchant = _seed_merchant('idempotent@test.com', 10000)
        key = str(uuid.uuid4())

        p1, created1 = create_payout(
            merchant_id=str(merchant.id),
            amount_paise=5000,
            bank_account_id='HDFC_001',
            idempotency_key=key,
        )
        p2, created2 = create_payout(
            merchant_id=str(merchant.id),
            amount_paise=5000,
            bank_account_id='HDFC_001',
            idempotency_key=key,
        )

        self.assertTrue(created1, "First call should return created=True")
        self.assertFalse(created2, "Second call should return created=False")
        self.assertEqual(p1.id, p2.id, "Both calls must return the same payout ID")

        payout_count = Payout.objects.filter(merchant=merchant).count()
        self.assertEqual(payout_count, 1, "Only one payout must exist in the DB")

        balance = get_available_balance(merchant)
        self.assertEqual(balance, 5000, f"Balance must be debited exactly once: expected 5000, got {balance}")

    def test_different_keys_create_separate_payouts(self):
        merchant = _seed_merchant('two_keys@test.com', 20000)
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        p1, _ = create_payout(str(merchant.id), 5000, 'HDFC_001', key1)
        p2, _ = create_payout(str(merchant.id), 5000, 'HDFC_002', key2)

        self.assertNotEqual(p1.id, p2.id)
        self.assertEqual(Payout.objects.filter(merchant=merchant).count(), 2)
        self.assertEqual(get_available_balance(merchant), 10000)
