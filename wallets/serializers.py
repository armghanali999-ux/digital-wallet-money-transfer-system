from rest_framework import serializers

from transactions.models import Transaction, WalletTransaction
from wallets.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    class Meta:
        model = Wallet
        fields = ["id", "owner_email", "balance", "currency", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "owner_email", "balance", "status", "created_at", "updated_at"]


class MoneySerializer(serializers.Serializer):
    wallet_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    currency = serializers.CharField(max_length=3)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class TransferSerializer(serializers.Serializer):
    sender_wallet_id = serializers.IntegerField(min_value=1)
    recipient_wallet_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AdjustmentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    reason = serializers.CharField(max_length=255, allow_blank=False)


class TransactionSerializer(serializers.ModelSerializer):
    direction = serializers.SerializerMethodField()
    class Meta:
        model = Transaction
        fields = ["id", "reference", "type", "status", "amount", "currency", "source_wallet_id", "destination_wallet_id", "direction", "description", "failure_code", "failure_reason", "created_at", "updated_at"]
    def get_direction(self, obj):
        user = self.context.get("request").user if self.context.get("request") else None
        if obj.type != Transaction.Type.TRANSFER or not user: return None
        return "OUTGOING" if obj.source_wallet and obj.source_wallet.owner_id == user.id else "INCOMING"
