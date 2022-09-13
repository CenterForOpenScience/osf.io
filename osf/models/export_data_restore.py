from __future__ import unicode_literals

import logging

import requests
from django.db import models

from addons.osfstorage.models import Region
from api.base.utils import waterbutler_api_url_for
from osf.models import (
    base,
    BaseFileNode,
    BaseFileVersionsThrough,
    ExportData,
    Institution,
    RdmFileTimestamptokenVerifyResult,
)
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
        db_table = "osf_export_data_restore"
        unique_together = ('export', 'destination', 'process_start')

    def __repr__(self):
        return f'"({self.export}-{self.destination})[{self.status}]"'

    __str__ = __repr__

    def extract_file_information_json_from_destination_storage(self):
        # Get region guid == institution guid
        destination_storage_guid = self.destination.guid
        # logger.debug(f'destination storage: {self.destination}')

        # Get Institution by guid
        institution = Institution.load(destination_storage_guid)

        if not institution:
            return None

        institution_json = {
            'id': institution.id,
            'guid': institution.guid,
            'name': institution.name,
        }

        export_data_json = {
            'institution': institution_json,
            'process_start': self.process_start.strftime('%Y-%m-%d %H:%M:%S'),
            'process_end': self.process_end.strftime('%Y-%m-%d %H:%M:%S') if self.process_end else None,
            'storage': {
                'name': self.destination.name,
                'type': self.destination.provider_full_name,
            },
            'projects_numb': 0,
            'files_numb': 0,
            'size': 0,
            'file_path': None,
        }

        file_info_json = {
            'institution': institution_json,
        }

        # get list FileVersion linked to destination storage
        file_versions = self.destination.fileversion_set.all()
        # but the creator must be affiliated with current institution
        file_versions = file_versions.filter(creator__affiliated_institutions___id=destination_storage_guid)
        # file_versions__ids = file_versions.values_list('id', flat=True)
        # logger.debug(f'file_versions: {file_versions.count()} {file_versions__ids}')

        # get list_basefilenode_id by file_versions__ids above via the BaseFileVersionsThrough model
        base_file_versions_set = BaseFileVersionsThrough.objects.filter(fileversion__in=file_versions)
        base_file_nodes__ids = base_file_versions_set.values_list('basefilenode_id', flat=True).distinct('basefilenode_id')

        # get project list
        projects = institution.nodes.filter(category='project')
        projects__ids = projects.values_list('id', flat=True)
        # logger.debug(f'projects: {projects.count()} {projects__ids}')
        destination_project_ids = set()

        # get base_file_nodes
        base_file_nodes = BaseFileNode.objects.filter(
            id__in=base_file_nodes__ids,
            target_object_id__in=projects__ids,
            deleted=None)
        # base_file_nodes__ids = base_file_nodes.values_list('id', flat=True)
        # logger.debug(f'base_file_nodes: {base_file_nodes.count()} {base_file_nodes__ids}')

        total_size = 0
        total_file = 0
        files = []
        # get file information
        for file in base_file_nodes:
            file_info = {
                'id': file.id,
                'path': file.path,
                'materialized_path': file.materialized_path,
                'name': file.name,
                'provider': file.provider,
                'created_at': file.created.strftime('%Y-%m-%d %H:%M:%S'),
                'modified_at': file.modified.strftime('%Y-%m-%d %H:%M:%S'),
                'project': {},
                'tags': [],
                'version': [],
                'size': 0,
                'location': {},
                'timestamp': {},
            }

            # project
            project = file.target
            destination_project_ids.add(project.id)
            project_info = {
                'id': project._id,
                'name': project.title,
            }
            file_info['project'] = project_info

            # file's tags
            if not file._state.adding:
                tags = list(file.tags.filter(system=False).values_list('name', flat=True))
                file_info['tags'] = tags

            # timestamp by project_id and file_id
            timestamp = RdmFileTimestamptokenVerifyResult.objects.filter(
                project_id=file.target.id, file_id=file.id).first()
            if timestamp:
                timestamp_info = {
                    'timestamp_token': timestamp.timestamp_token,
                    'verify_user': timestamp.verify_user,
                    'verify_date': timestamp.verify_date,
                    'updated_at': timestamp.verify_file_created_at,
                }
                file_info['timestamp'] = timestamp_info

            # file versions
            file_versions = file.versions.order_by('-created')
            file_versions_info = []
            for version in file_versions:
                file_version_thru = version.get_basefilenode_version(file)
                version_info = {
                    'identifier': version.identifier,
                    'created_at': version.created.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': version.size,
                    'version_name': file_version_thru.version_name if file_version_thru else file.name,
                    'contributor': version.creator.username,
                    'metadata': version.metadata,
                    'location': version.location,
                }
                file_versions_info.append(version_info)
                total_file += 1
                total_size += version.size

            file_info['version'] = file_versions_info
            file_info['size'] = file_versions_info[-1]['size']
            file_info['location'] = file_versions_info[-1]['location']
            files.append(file_info)

        file_info_json['files'] = files

        export_data_json['files_numb'] = total_file
        export_data_json['size'] = total_size
        export_data_json['projects_numb'] = len(destination_project_ids)

        return export_data_json, file_info_json

    @property
    def process_start_timestamp(self):
        return self.process_start.strftime('%s')

    @property
    def process_start_display(self):
        return self.process_start.strftime('%Y%m%dT%H%M%S')

    def transfer_export_data_file_to_destination(self, cookies, project_id, provider, folder_path, file_name, file_data, **kwargs):
        """Upload data file to the destination storage"""
        url = waterbutler_api_url_for(
            project_id, provider, path=folder_path,
            name=file_name,
            kind='file',
            _internal=True, location_id=self.destination.id,
            **kwargs
        )
        return requests.put(url, data=file_data, cookies=cookies)

    def update(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.save()
