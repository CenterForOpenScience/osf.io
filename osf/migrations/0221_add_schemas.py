import logging

from django.db import migrations

logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0219_auto_20201020_1836'),
    ]

    operations = []
