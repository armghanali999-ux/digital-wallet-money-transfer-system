from django.db.models import Q, Sum

from transactions.models import Transaction
from wallets.models import FinancialConfiguration, Wallet


class WalletRepository:
    @staticmethod
    def owned(wallet_id, user):
        return Wallet.objects.filter(id=wallet_id, owner=user).first()

    @staticmethod
    def lock_many(ids):
        return {w.id: w for w in Wallet.objects.select_for_update().filter(id__in=sorted(set(ids))).order_by("id")}

    @staticmethod
    def daily_completed_total(wallet, transaction_type, since):
        return Transaction.objects.filter(
            source_wallet=wallet, type=transaction_type, status=Transaction.Status.COMPLETED, created_at__gte=since
        ).aggregate(total=Sum("amount"))["total"] or 0


class ConfigurationRepository:
    @staticmethod
    def get(key):
        obj = FinancialConfiguration.objects.filter(key=key).first()
        return obj.value if obj else FinancialConfiguration.DEFAULTS[key]
