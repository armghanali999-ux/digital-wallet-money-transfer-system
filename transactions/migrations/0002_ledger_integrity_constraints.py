from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("transactions", "0001_initial")]
    operations = [
        migrations.AddConstraint(model_name="wallettransaction", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="ledger_amount_positive")),
        migrations.AddConstraint(model_name="wallettransaction", constraint=models.CheckConstraint(condition=models.Q(("balance_before__gte", 0)), name="ledger_before_nonnegative")),
        migrations.AddConstraint(model_name="wallettransaction", constraint=models.CheckConstraint(condition=models.Q(("balance_after__gte", 0)), name="ledger_after_nonnegative")),
    ]
