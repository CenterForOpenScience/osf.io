# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-12 17:18
from __future__ import unicode_literals
import progressbar

from django.db import migrations
from bulk_update.helper import bulk_update


def reverse_func(state, schema):
    PageCounter = state.get_model('osf', 'PageCounter')

    pagecounters = PageCounter.objects.all()
    batch = []
    for pc in pagecounters:
        pc.guid_id = None
        pc.file_id = None
        pc.version = None
        batch.append(pc)

    bulk_update(batch, update_fields=['guid_id', 'file_id', 'version'], batch_size=10000)


def separate_pagecounter_id(state, schema):
    """
    Splits the data in pagecounter _id field of form action:guid_id:file_id:version into
    four new columns: action(char), resource(fk), file(fk), version(int)
    """
    Guid = state.get_model('osf', 'Guid')
    BaseFileNode = state.get_model('osf.BaseFileNode')
    PageCounter = state.get_model('osf', 'PageCounter')

    pagecounters = PageCounter.objects.all()
    progress_bar = progressbar.ProgressBar(maxval=len(pagecounters) or 1).start()
    batch = []

    for i, pc in enumerate(pagecounters, 1):
        id_array = pc._id.split(':')

        pc.action = id_array[0]
        pc.guid_id = Guid.objects.get(_id=id_array[1]).id
        pc.file_id = BaseFileNode.objects.get(_id=id_array[2]).id
        pc.version = id_array[3] if len(id_array) == 4 else None
        batch.append(pc)
        progress_bar.update(i)
    bulk_update(batch, update_fields=['action', 'guid_id', 'file_id', 'version'], batch_size=10000)
    progress_bar.finish()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0154_pagecounter_schema'),
    ]

    operations = [
        migrations.RunPython(
            separate_pagecounter_id, reverse_func
        ),
    ]
