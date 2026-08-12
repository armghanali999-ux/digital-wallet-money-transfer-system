from django.conf import settings
from django.db import models


class AdministrativeAudit(models.Model):
    class Action(models.TextChoices):
        FREEZE = "FREEZE", "Freeze"
        UNFREEZE = "UNFREEZE", "Unfreeze"
        BALANCE_ADJUSTMENT = "BALANCE_ADJUSTMENT", "Balance adjustment"

    administrator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    wallet = models.ForeignKey("wallets.Wallet", on_delete=models.PROTECT, related_name="admin_audits")
    action = models.CharField(max_length=24, choices=Action.choices)
    reason = models.CharField(max_length=255)
    balance_before = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    balance_after = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    transaction = models.ForeignKey("transactions.Transaction", null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

# Create your models here.
