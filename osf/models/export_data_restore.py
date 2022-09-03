from __future__ import unicode_literals

import logging

from django.db import models

from addons.osfstorage.models import Region
from osf.models import base, ExportData
from osf.models.export_data import SecondDateTimeField

logger = logging.getLogger(__name__)

__all__ = [
    'ExportDataRestore',
]


class ExportDataRestore(base.BaseModel):
    export = models.ForeignKey(ExportData, on_delete=models.CASCADE)
    destination = models.ForeignKey(Region, on_delete=models.CASCADE)
    process_start = SecondDateTimeField(auto_now=False, auto_now_add=True)
    process_end = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    last_check = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    status = models.CharField(choices=ExportData.EXPORT_DATA_STATUS_CHOICES, max_length=255)
    task_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('export', 'destination', 'process_start')

    def __repr__(self):
        return f'"({self.export}-{self.destination})[{self.status}]"'

    __str__ = __repr__

    @property
    def process_start_timestamp(self):
        return self.process_start.strftime('%s')

    @property
    def process_start_display(self):
        return self.process_start.strftime('%Y%m%dT%H%M%S')
