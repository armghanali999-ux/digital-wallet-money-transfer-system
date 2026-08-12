from django.contrib import admin

from transactions.models import IdempotencyRecord, Transaction, WalletTransaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "type", "status", "amount", "currency", "created_at")
    list_filter = ("type", "status", "currency")
    search_fields = ("reference", "failure_code", "failure_reason")
    readonly_fields = [field.name for field in Transaction._meta.fields]


@admin.register(WalletTransaction)
class LedgerAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in WalletTransaction._meta.fields]


admin.site.register(IdempotencyRecord)
