from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class Wallet(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FROZEN = "FROZEN", "Frozen"
        CLOSED = "CLOSED", "Closed"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="wallets")
    balance = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    active_currency = models.CharField(max_length=3, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(balance__gte=0), name="wallet_balance_nonnegative"),
            models.UniqueConstraint(fields=["owner", "active_currency"], name="unique_active_wallet_currency"),
        ]
        indexes = [models.Index(fields=["owner", "status"]), models.Index(fields=["currency"])]

    def save(self, *args, **kwargs):
        self.currency = self.currency.upper()
        self.active_currency = self.currency if self.status == self.Status.ACTIVE else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.owner.email} - {self.currency}"


class FinancialConfiguration(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

    DEFAULTS = {
        "SUPPORTED_CURRENCIES": "USD,PKR,EUR,GBP",
        "MAX_SINGLE_DEPOSIT": "1000000.00",
        "MAX_SINGLE_WITHDRAWAL": "100000.00",
        "MAX_DAILY_WITHDRAWAL": "250000.00",
        "MAX_SINGLE_TRANSFER": "250000.00",
        "MAX_DAILY_TRANSFER": "500000.00",
    }

# Create your models here.
