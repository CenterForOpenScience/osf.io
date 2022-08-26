from __future__ import unicode_literals

import logging

from django.db import models
from django.db.models import DateTimeField

from addons.osfstorage.models import Region
from osf.models import base, ExportDataLocation

logger = logging.getLogger(__name__)

__all__ = [
    'DateTruncMixin',
    'SecondDateTimeField',
    'ExportData',
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
    STATUS_RUNNING = 'Running'
    STATUS_STOPPING = 'Stopping'
    STATUS_CHECKING = 'Checking'
    STATUS_STOPPED = 'Stopped'
    STATUS_COMPLETED = 'Completed'

    EXPORT_DATA_STATUS_CHOICES = (
        (STATUS_RUNNING, STATUS_RUNNING.title()),
        (STATUS_STOPPING, STATUS_STOPPING.title()),
        (STATUS_CHECKING, STATUS_CHECKING.title()),
        (STATUS_STOPPED, STATUS_STOPPED.title()),
        (STATUS_COMPLETED, STATUS_COMPLETED.title()),
    )

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

    @property
    def process_start_timestamp(self):
        return self.process_start.strftime('%s')

    @property
    def export_data_folder(self):
        return f'export_{self.source.id}_{self.process_start_timestamp}'

    def get_export_data_filename(self, institution_guid):
        return f'export_data_{institution_guid}_{self.process_start_timestamp}.json'

    def get_file_info_filename(self, institution_guid):
        return f'file_info_{institution_guid}_{self.process_start_timestamp}.json'
