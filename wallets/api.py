from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import FilterSet, DateFilter, NumberFilter
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.domain.exceptions import DomainError
from accounts.models import User
from transactions.models import Transaction
from wallets.models import Wallet
from wallets.serializers import MoneySerializer, TransactionSerializer, TransferSerializer, WalletSerializer
from wallets.services import create_wallet, deposit, transfer, withdraw


class WalletListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = WalletSerializer
    def get_queryset(self): return Wallet.objects.filter(owner=self.request.user).order_by("currency", "id")
    def perform_create(self, serializer): serializer.instance = create_wallet(self.request.user, serializer.validated_data["currency"])


class WalletDetailAPIView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    def get_queryset(self): return Wallet.objects.filter(owner=self.request.user)


class FinancialAPIView(APIView):
    operation = None
    serializer_class = MoneySerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data); serializer.is_valid(raise_exception=True)
        data = serializer.validated_data; key = request.headers.get("Idempotency-Key")
        if self.operation == "deposit": result = deposit(request.user, data["wallet_id"], data["amount"], data["currency"], key, data.get("description", ""))
        elif self.operation == "withdraw": result = withdraw(request.user, data["wallet_id"], data["amount"], data["currency"], key, data.get("description", ""))
        else: result = transfer(request.user, data["sender_wallet_id"], data["recipient_wallet_id"], data["amount"], key, data.get("description", ""))
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class DepositAPIView(FinancialAPIView): operation = "deposit"
class WithdrawAPIView(FinancialAPIView): operation = "withdraw"
class TransferAPIView(FinancialAPIView): operation = "transfer"; serializer_class = TransferSerializer


class TransactionFilter(FilterSet):
    start_date = DateFilter(method="filter_start_date")
    end_date = DateFilter(method="filter_end_date")
    min_amount = NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = NumberFilter(field_name="amount", lookup_expr="lte")
    class Meta:
        model = Transaction
        fields = ["type", "status", "start_date", "end_date", "min_amount", "max_amount"]

    def filter_start_date(self, queryset, name, value):
        boundary = timezone.make_aware(datetime.combine(value, time.min))
        return queryset.filter(created_at__gte=boundary)

    def filter_end_date(self, queryset, name, value):
        boundary = timezone.make_aware(datetime.combine(value + timedelta(days=1), time.min))
        return queryset.filter(created_at__lt=boundary)


class TransactionListAPIView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    def get_queryset(self):
        qs = Transaction.objects.select_related("source_wallet__owner", "destination_wallet__owner")
        if not (self.request.user.is_staff or self.request.user.role == User.Role.ADMIN):
            qs = qs.filter(Q(source_wallet__owner=self.request.user) | Q(destination_wallet__owner=self.request.user)).distinct()
        search = self.request.query_params.get("reference")
        return qs.filter(reference__icontains=search) if search else qs


class TransactionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    lookup_field = "reference"
    def get_queryset(self):
        qs = Transaction.objects.all()
        if self.request.user.is_staff or self.request.user.role == User.Role.ADMIN:
            return qs
        return qs.filter(Q(source_wallet__owner=self.request.user) | Q(destination_wallet__owner=self.request.user)).distinct()
