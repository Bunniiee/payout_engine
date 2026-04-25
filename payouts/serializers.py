from rest_framework import serializers

from .models import Payout, LedgerEntry, Merchant
from .services import get_available_balance, get_held_balance


class PayoutSerializer(serializers.ModelSerializer):
    merchant_id = serializers.UUIDField(source='merchant.id', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'merchant_id', 'amount_paise', 'bank_account_id',
            'status', 'idempotency_key', 'attempts',
            'processing_started_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'merchant_id', 'status', 'attempts',
            'processing_started_at', 'created_at', 'updated_at',
        ]


class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=200, allow_blank=False)


class LedgerEntrySerializer(serializers.ModelSerializer):
    payout_id = serializers.UUIDField(source='payout.id', allow_null=True, read_only=True)

    class Meta:
        model = LedgerEntry
        fields = ['id', 'amount_paise', 'entry_type', 'payout_id', 'created_at']


class MerchantSerializer(serializers.ModelSerializer):
    available_balance_paise = serializers.SerializerMethodField()
    held_balance_paise = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'available_balance_paise', 'held_balance_paise']

    def get_available_balance_paise(self, obj):
        return get_available_balance(obj)

    def get_held_balance_paise(self, obj):
        return get_held_balance(obj)
