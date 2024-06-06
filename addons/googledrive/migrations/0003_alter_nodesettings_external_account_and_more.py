# Generated by Django 4.2.13 on 2024-06-06 18:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0020_abstractprovider_advertise_on_discover_page'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('addons_googledrive', '0002_auto_20220817_1915'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodesettings',
            name='external_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_node_settings', to='osf.externalaccount'),
        ),
        migrations.AlterField(
            model_name='nodesettings',
            name='owner',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_node_settings', to='osf.abstractnode'),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='owner',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_user_settings', to=settings.AUTH_USER_MODEL),
        ),
    ]
