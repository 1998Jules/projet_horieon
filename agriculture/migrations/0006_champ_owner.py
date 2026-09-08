from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("agriculture", "0005_remove_champ_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="champ",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="champs_agriculture",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
