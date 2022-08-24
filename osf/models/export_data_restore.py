from __future__ import unicode_literals

import logging

from django.db import models

from addons.osfstorage.models import Region
from osf.models import base, ExportData

logger = logging.getLogger(__name__)

EXPORT_DATA_STATUS_CHOICES = [
    ('Running', 'Running'),
    ('Stopping', 'Stopping'),
    ('Checking', 'Checking'),
    ('Stopped', 'Stopped'),
    ('Completed', 'Completed'),
]


class ExportDataRestore(base.BaseModel):
    export = models.ForeignKey(ExportData, on_delete=models.CASCADE)
    destination = models.ForeignKey(Region, on_delete=models.CASCADE)
    process_start = models.DateTimeField(auto_now=False, auto_now_add=True)
    process_end = models.DateTimeField(auto_now=False, auto_now_add=False)
    last_check = models.DateTimeField(auto_now=False, auto_now_add=False, null=True)
    status = models.CharField(choices=EXPORT_DATA_STATUS_CHOICES, max_length=255)

    class Meta:
        unique_together = ('export', 'destination', 'process_start')

    def __repr__(self):
        return f'"({self.export}-{self.destination})[{self.status}]"'

    __str__ = __repr__
