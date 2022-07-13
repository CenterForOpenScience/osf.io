import logging

from django.db import migrations

logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0226_auto_20210224_1610'),
    ]

    operations = []
