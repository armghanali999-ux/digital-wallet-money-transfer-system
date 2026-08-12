from django.contrib import admin

from administration.models import AdministrativeAudit


@admin.register(AdministrativeAudit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ("administrator", "wallet", "action", "reason", "created_at")
    list_filter = ("action",)
    readonly_fields = [field.name for field in AdministrativeAudit._meta.fields]
