from django.db import migrations


DEFAULTS = {
    "SUPPORTED_CURRENCIES": "USD,PKR,EUR,GBP",
    "MAX_SINGLE_DEPOSIT": "1000000.00",
    "MAX_SINGLE_WITHDRAWAL": "100000.00",
    "MAX_DAILY_WITHDRAWAL": "250000.00",
    "MAX_SINGLE_TRANSFER": "250000.00",
    "MAX_DAILY_TRANSFER": "500000.00",
}


def seed_configuration(apps, schema_editor):
    configuration = apps.get_model("wallets", "FinancialConfiguration")
    for key, value in DEFAULTS.items():
        configuration.objects.get_or_create(key=key, defaults={"value": value})


class Migration(migrations.Migration):
    dependencies = [("wallets", "0001_initial")]
    operations = [migrations.RunPython(seed_configuration, migrations.RunPython.noop)]
