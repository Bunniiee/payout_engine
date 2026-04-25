import uuid

from django.http import Http404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import InsufficientFunds
from .models import Merchant, Payout, LedgerEntry
from .serializers import (
    MerchantSerializer,
    PayoutSerializer,
    PayoutCreateSerializer,
    LedgerEntrySerializer,
)
from .services import create_payout
from .tasks import process_payout


def get_merchant_from_request(request):
    merchant_id = request.headers.get('X-Merchant-Id') or request.headers.get('X-Merchant-ID')
    if not merchant_id:
        raise Http404("X-Merchant-ID header is required")
    try:
        return Merchant.objects.get(id=merchant_id)
    except (Merchant.DoesNotExist, Exception):
        raise Http404(f"Merchant {merchant_id} not found")


class MerchantListView(APIView):
    def get(self, request):
        merchants = Merchant.objects.all().order_by('name')
        serializer = MerchantSerializer(merchants, many=True)
        return Response(serializer.data)


class MerchantMeView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        serializer = MerchantSerializer(merchant)
        return Response(serializer.data)


class PayoutListCreateView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        payouts = Payout.objects.filter(merchant=merchant).order_by('-created_at')
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(payouts, request)
        serializer = PayoutSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            return Response(
                {'error': 'Idempotency-Key must be a valid UUID'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        merchant_id = request.headers.get('X-Merchant-Id') or request.headers.get('X-Merchant-ID')
        if not merchant_id:
            return Response(
                {'error': 'X-Merchant-ID header is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PayoutCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            payout, created = create_payout(
                merchant_id=merchant_id,
                amount_paise=serializer.validated_data['amount_paise'],
                bank_account_id=serializer.validated_data['bank_account_id'],
                idempotency_key=idempotency_key,
            )
        except Merchant.DoesNotExist:
            return Response(
                {'error': f'Merchant not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except InsufficientFunds as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if created:
            process_payout.delay(str(payout.id))

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(PayoutSerializer(payout).data, status=response_status)


class PayoutDetailView(RetrieveAPIView):
    serializer_class = PayoutSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        merchant = get_merchant_from_request(self.request)
        return Payout.objects.filter(merchant=merchant)


class LedgerListView(ListAPIView):
    serializer_class = LedgerEntrySerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        merchant = get_merchant_from_request(self.request)
        return LedgerEntry.objects.filter(merchant=merchant).order_by('-created_at')
