from __future__ import unicode_literals

import logging

from django.db import models

from addons.osfstorage.models import Region
from osf.models import base, ExportDataLocation

logger = logging.getLogger(__name__)

EXPORT_DATA_STATUS_CHOICES = [
    ('Running', 'Running'),
    ('Stopping', 'Stopping'),
    ('Checking', 'Checking'),
    ('Stopped', 'Stopped'),
    ('Completed', 'Completed'),
]


class ExportData(base.BaseModel):
    source_id = models.ForeignKey(Region, on_delete=models.CASCADE)
    location_id = models.ForeignKey(ExportDataLocation, on_delete=models.CASCADE)
    process_start = models.DateTimeField(auto_now=False, auto_now_add=False)
    process_end = models.DateTimeField(auto_now=False, auto_now_add=False)
    last_check = models.DateTimeField(auto_now=False, auto_now_add=False)
    status = models.CharField(choices=EXPORT_DATA_STATUS_CHOICES, max_length=63)
    export_file = models.CharField(max_length=255, null=True, blank=True)
    project_number = models.PositiveIntegerField()
    file_number = models.PositiveIntegerField()
    total_size = models.PositiveIntegerField()
    is_deleted = models.BooleanField(default=False)

    def __repr__(self):
        return f'"({self.source_id}-{self.location_id})"'

    __str__ = __repr__

    class Meta:
        unique_together = ('source_id', 'location_id')
