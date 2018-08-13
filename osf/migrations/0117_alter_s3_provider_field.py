# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import migrations


def update_provider_fields(apps, *args, **kwargs):
    ExternalAccount = apps.get_model('osf', 'externalaccount')
    for account in ExternalAccount.objects.filter(provider='s3'):
        account.provider_id = 'https://{}@s3.amazonaws.com:443'.format(
            account.provider_id
        )
        account.save()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0116_merge_20180703_2258')
    ]

    operations = [
        migrations.RunPython(update_provider_fields)
    ]
