from django.db import migrations, models
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0044_notification_scheduled'),
    ]

    operations = [
        migrations.AddField(
            model_name='osfuser',
            name='date_orcid_initial_authorized',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='osfuser',
            name='date_orcid_last_authorized',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='osfuser',
            name='orcid_token_stored',
            field=models.BooleanField(default=False),
        ),
    ]
