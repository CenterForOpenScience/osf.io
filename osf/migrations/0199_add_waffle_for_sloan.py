from __future__ import unicode_literals

from django.db import migrations
from waffle.models import Flag

from osf.features import (
    SLOAN_COI,
    SLOAN_DATA,
    SLOAN_PREREG
)

def remove_sloan_flags_and_groups(*args, **kwargs):
    Flag.objects.get(name=SLOAN_COI).delete()
    Flag.objects.get(name=SLOAN_DATA).delete()
    Flag.objects.get(name=SLOAN_PREREG).delete()


def add_sloan_flags_and_groups(*args, **kwargs):
    Flag.objects.create(name=SLOAN_COI, percent=50, everyone=False).save()
    Flag.objects.create(name=SLOAN_DATA, percent=50, everyone=False).save()
    Flag.objects.create(name=SLOAN_PREREG, percent=50, everyone=False).save()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0198_abstractprovider_in_sloan_study'),
    ]

    operations = [
        migrations.RunPython(add_sloan_flags_and_groups, remove_sloan_flags_and_groups),
    ]
