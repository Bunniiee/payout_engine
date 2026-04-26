from django.core.management.base import BaseCommand
from payouts.models import Merchant, LedgerEntry


SEED_DATA = [
    {
        'name': 'Arjun Mehta',
        'email': 'arjun@example.com',
        'credits': [80000, 120000, 150000, 95000, 75000, 110000],
    },
    {
        'name': 'Priya Sharma',
        'email': 'priya@example.com',
        'credits': [200000, 175000, 140000, 95000, 80000, 60000, 250000],
    },
    {
        'name': 'Rohan Das',
        'email': 'rohan@example.com',
        'credits': [90000, 75000, 65000, 70000, 100000],
    },
]


class Command(BaseCommand):
    help = 'Seed database with merchants and initial credit history'

    def handle(self, *args, **options):
        for data in SEED_DATA:
            merchant, created = Merchant.objects.get_or_create(
                email=data['email'],
                defaults={'name': data['name']},
            )
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f"{action} merchant: {merchant.name} ({merchant.id})")

            if created:
                for amount in data['credits']:
                    LedgerEntry.objects.create(
                        merchant=merchant,
                        amount_paise=amount,
                        entry_type=LedgerEntry.CREDIT,
                        payout=None,
                    )
                total = sum(data['credits'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Seeded {len(data['credits'])} credits totalling {total} paise (INR {total/100:.2f})"
                    )
                )
            else:
                from django.db.models import Sum
                balance = LedgerEntry.objects.filter(merchant=merchant).aggregate(
                    t=Sum('amount_paise')
                )['t'] or 0
                self.stdout.write(f"  Current balance: {balance} paise (INR {balance/100:.2f})")

        self.stdout.write(self.style.SUCCESS('\nSeed complete.'))
