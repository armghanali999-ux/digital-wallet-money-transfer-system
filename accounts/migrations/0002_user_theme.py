from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="user",
            name="theme",
            field=models.CharField(
                choices=[
                    ("emerald_finance", "Emerald Finance"),
                    ("navy_teal_fintech", "Navy Teal Fintech"),
                    ("indigo_professional", "Indigo Professional"),
                    ("premium_black_gold", "Premium Black Gold"),
                    ("classic_blue", "Classic Blue"),
                    ("dark_mode", "Dark Mode"),
                ],
                default="emerald_finance",
                max_length=32,
            ),
        ),
    ]
