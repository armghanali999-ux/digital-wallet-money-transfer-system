from django.conf import settings
from django.db import models
from django.db.models import Q


class ReferenceSequence(models.Model):
    business_date = models.DateField(unique=True)
    last_value = models.PositiveBigIntegerField(default=0)


class Transaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
        TRANSFER = "TRANSFER", "Transfer"
        BALANCE_ADJUSTMENT = "BALANCE_ADJUSTMENT", "Balance adjustment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    reference = models.CharField(max_length=32, unique=True)
    type = models.CharField(max_length=24, choices=Type.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3)
    source_wallet = models.ForeignKey("wallets.Wallet", null=True, blank=True, on_delete=models.PROTECT, related_name="outgoing_transactions")
    destination_wallet = models.ForeignKey("wallets.Wallet", null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_transactions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions")
    description = models.CharField(max_length=255, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "type", "created_at"]), models.Index(fields=["reference"])]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="transaction_amount_positive")]


class WalletTransaction(models.Model):
    class Direction(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="ledger_entries")
    wallet = models.ForeignKey("wallets.Wallet", on_delete=models.PROTECT, related_name="ledger_entries")
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    balance_before = models.DecimalField(max_digits=19, decimal_places=4)
    balance_after = models.DecimalField(max_digits=19, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transaction", "wallet", "direction"], name="unique_ledger_leg"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="ledger_amount_positive"),
            models.CheckConstraint(condition=Q(balance_before__gte=0), name="ledger_before_nonnegative"),
            models.CheckConstraint(condition=Q(balance_after__gte=0), name="ledger_after_nonnegative"),
        ]


class IdempotencyRecord(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operation = models.CharField(max_length=32)
    key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    transaction = models.OneToOneField(Transaction, null=True, blank=True, on_delete=models.PROTECT)
    response_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["actor", "operation", "key"], name="unique_actor_operation_key")]

# Create your models here.
