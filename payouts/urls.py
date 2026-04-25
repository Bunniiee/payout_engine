from django.urls import path
from .views import (
    MerchantListView,
    MerchantMeView,
    PayoutListCreateView,
    PayoutDetailView,
    LedgerListView,
)

urlpatterns = [
    path('merchants/', MerchantListView.as_view(), name='merchant-list'),
    path('merchants/me/', MerchantMeView.as_view(), name='merchant-me'),
    path('payouts/', PayoutListCreateView.as_view(), name='payout-list-create'),
    path('payouts/<uuid:pk>/', PayoutDetailView.as_view(), name='payout-detail'),
    path('ledger/', LedgerListView.as_view(), name='ledger-list'),
]
