from __future__ import unicode_literals

import logging

from django.db import models
from django.db.models import DateTimeField

from addons.osfstorage.models import Region
from osf.models import base, ExportDataLocation

logger = logging.getLogger(__name__)

__all__ = [
    'STATUS_RUNNING',
    'STATUS_STOPPING',
    'STATUS_CHECKING',
    'STATUS_STOPPED',
    'STATUS_COMPLETED',
    'EXPORT_DATA_STATUS_CHOICES',
    'DateTruncMixin',
    'SecondDateTimeField',
    'ExportData',
]

STATUS_RUNNING = 'Running'
STATUS_STOPPING = 'Stopping'
STATUS_CHECKING = 'Checking'
STATUS_STOPPED = 'Stopped'
STATUS_COMPLETED = 'Completed'

EXPORT_DATA_STATUS_CHOICES = [
    (STATUS_RUNNING, STATUS_RUNNING),
    (STATUS_STOPPING, STATUS_STOPPING),
    (STATUS_CHECKING, STATUS_CHECKING),
    (STATUS_STOPPED, STATUS_STOPPED),
    (STATUS_COMPLETED, STATUS_COMPLETED),
]


class DateTruncMixin:
    def truncate_date(self, dt):
        return dt

    def to_python(self, value):
        value = super().to_python(value)
        if value is not None:
            return self.truncate_date(value)
        return value


class SecondDateTimeField(DateTruncMixin, DateTimeField):
    def truncate_date(self, dt):
        return dt.replace(microsecond=0)


class ExportData(base.BaseModel):
    source = models.ForeignKey(Region, on_delete=models.CASCADE)
    location = models.ForeignKey(ExportDataLocation, on_delete=models.CASCADE)
    process_start = SecondDateTimeField(auto_now=False, auto_now_add=True)
    process_end = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    last_check = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    status = models.CharField(choices=EXPORT_DATA_STATUS_CHOICES, max_length=255)
    export_file = models.CharField(max_length=255, null=True, blank=True)
    project_number = models.PositiveIntegerField(default=0)
    file_number = models.PositiveIntegerField(default=0)
    total_size = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('source', 'location', 'process_start')

    def __repr__(self):
        return f'"({self.source}-{self.location})[{self.status}]"'

    __str__ = __repr__
