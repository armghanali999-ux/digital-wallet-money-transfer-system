from django.contrib import admin

from wallets.models import FinancialConfiguration, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "balance", "currency", "status")
    list_filter = ("currency", "status")
    search_fields = ("owner__email",)
    readonly_fields = ("owner", "balance", "currency", "status", "active_currency", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(FinancialConfiguration)
