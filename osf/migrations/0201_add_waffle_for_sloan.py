from __future__ import unicode_literals

from django.db import migrations
from waffle.models import Flag

from osf.features import (
    SLOAN_COI_DISPLAY,
    SLOAN_DATA_DISPLAY,
    SLOAN_PREREG_DISPLAY
)

def remove_sloan_flags_and_groups(*args, **kwargs):
    Flag.objects.get(name=SLOAN_COI_DISPLAY).delete()
    Flag.objects.get(name=SLOAN_DATA_DISPLAY).delete()
    Flag.objects.get(name=SLOAN_PREREG_DISPLAY).delete()


def add_sloan_flags_and_groups(*args, **kwargs):
    Flag.objects.create(name=SLOAN_COI_DISPLAY, percent=50, everyone=False).save()
    Flag.objects.create(name=SLOAN_DATA_DISPLAY, percent=50, everyone=False).save()
    Flag.objects.create(name=SLOAN_PREREG_DISPLAY, percent=50, everyone=False).save()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0200_abstractprovider_in_sloan_study'),
    ]

    operations = [
        migrations.RunPython(add_sloan_flags_and_groups, remove_sloan_flags_and_groups),
    ]
