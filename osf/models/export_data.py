from __future__ import unicode_literals

import logging
import os.path

import requests
from django.db import models
from django.db.models import DateTimeField

from addons.osfstorage.models import Region
from osf.models import base, ExportDataLocation
from api.base.utils import waterbutler_api_url_for

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
    STATUS_ERROR = 'Error'

    EXPORT_DATA_STATUS_CHOICES = (
        (STATUS_RUNNING, STATUS_RUNNING.title()),
        (STATUS_STOPPING, STATUS_STOPPING.title()),
        (STATUS_CHECKING, STATUS_CHECKING.title()),
        (STATUS_STOPPED, STATUS_STOPPED.title()),
        (STATUS_COMPLETED, STATUS_COMPLETED.title()),
        (STATUS_ERROR, STATUS_ERROR.title()),
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
    task_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('source', 'location', 'process_start')

    def __repr__(self):
        return f'"({self.source}-{self.location})[{self.status}]"'

    __str__ = __repr__

    @property
    def process_start_timestamp(self):
        return self.process_start.strftime('%Y%m%dT%H%M%S')

    @property
    def export_data_folder_name(self):
        return f'export_{self.source.id}_{self.process_start_timestamp}'

    @property
    def export_data_folder_path(self):
        return f'/export_{self.source.id}_{self.process_start_timestamp}/'

    def create_export_data_folder(self, cookies, **kwargs):
        node_id = 'export_location'
        provider = self.location.provider_name
        path = '/'
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            name=self.export_data_folder_name,
            kind='folder', meta='',
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.put(url, cookies=cookies)

    def delete_export_data_folder(self, cookies, **kwargs):
        node_id = 'export_location'
        provider = self.location.provider_name
        path = self.export_data_folder_path
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            confirm_delete=1,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.delete(url, cookies=cookies)

    def get_export_data_filename(self, institution_guid=None):
        if not institution_guid:
            institution_guid = self.source.guid
        return f'export_data_{institution_guid}_{self.process_start_timestamp}.json'

    def get_export_data_file_path(self, institution_guid=None):
        if not institution_guid:
            institution_guid = self.source.guid
        return os.path.join(self.export_data_folder_name, self.get_export_data_filename(institution_guid))

    def get_file_info_filename(self, institution_guid=None):
        if not institution_guid:
            institution_guid = self.source.guid
        return f'file_info_{institution_guid}_{self.process_start_timestamp}.json'

    def upload_export_data_file(self, cookies, file_path, **kwargs):
        node_id = 'export_location'
        provider = self.location.provider_name
        path = self.export_data_folder_path
        file_name = kwargs.get('file_name', self.get_export_data_filename(self.location.institution_guid))
        with open(file_path, 'r') as fp:
            url = waterbutler_api_url_for(
                node_id, provider, path=path,
                name=file_name,
                kind='file',
                _internal=True, location_id=self.location.id,
                **kwargs
            )
            return requests.put(url, data=fp, cookies=cookies)

    def upload_file_info_file(self, cookies, file_path, **kwargs):
        file_name = self.get_file_info_filename(self.location.institution_guid)
        kwargs.setdefault('file_name', file_name)
        return self.upload_export_data_file(cookies, file_path, **kwargs)

    def read_file_info(self, cookies, **kwargs):
        node_id = 'export_location'
        provider = self.location.provider_name
        filename_info = self.get_file_info_filename(self.location.institution_guid)
        path = self.export_data_folder_path + filename_info
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.get(url, cookies=cookies, stream=True)

    def delete_file_export(self, cookies, **kwargs):
        node_id = 'export_location'
        provider = self.location.provider_name
        filename_info = self.get_file_info_filename(self.location.institution_guid)
        path = self.export_data_folder_path + filename_info
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.delete(url, cookies=cookies)
