from __future__ import unicode_literals

import logging

import requests
from django.db import models
from django.db.models import Q

from addons.osfstorage.models import Region
from api.base.utils import waterbutler_api_url_for
from osf.models import (
    base,
    BaseFileNode,
    BaseFileVersionsThrough,
    ExportData,
    Institution,
    RdmFileTimestamptokenVerifyResult,
    AbstractNode,
)
from osf.models.export_data import SecondDateTimeField, get_hashes_from_metadata
from website.settings import INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD

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
    creator = models.ForeignKey('OSFUser', on_delete=models.CASCADE)

    class Meta:
        db_table = 'osf_export_data_restore'
        unique_together = ('export', 'destination', 'process_start')

    def __repr__(self):
        return f'"({self.export}-{self.destination})[{self.status}]"'

    __str__ = __repr__

    def extract_file_information_json_from_destination_storage(self, **kwargs):
        # Get region guid == institution guid
        destination_storage_guid = self.destination.guid

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

        # get project list, includes public/private/deleted projects
        projects = institution.nodes.filter(type='osf.node', is_deleted=False)
        institution_users = institution.osfuser_set.all()
        institution_users_projects = AbstractNode.objects.filter(type='osf.node', is_deleted=False, affiliated_institutions=None, creator__in=institution_users)
        # Combine two project lists and remove duplicates if have
        projects = projects.union(institution_users_projects)
        projects__ids = projects.values_list('id', flat=True)

        # get folder nodes
        base_folder_nodes = BaseFileNode.objects.filter(
            # type='osf.{}folder'.format(self.source.provider_short_name),
            type__endswith='folder',
            target_object_id__in=projects__ids,
        ).exclude(
            # exclude deleted folder
            Q(deleted__isnull=False) | Q(deleted_on__isnull=False) | Q(deleted_by_id__isnull=False),
        )
        folders = []
        for folder in base_folder_nodes:
            folder_info = {
                'path': folder.path,
                'materialized_path': folder.materialized_path,
                'project': {}
            }
            # project
            project = folder.target
            project_info = {
                'id': project._id,
                'name': project.title,
            }
            folder_info['project'] = project_info
            folders.append(folder_info)

        if self.destination.provider_name in INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD:
            # Bulk-mount storage
            # get list FileVersion linked to destination storage
            file_versions = self.destination.fileversion_set.all()
            # but the creator must be affiliated with current institution
            file_versions = file_versions.filter(creator__affiliated_institutions___id=destination_storage_guid)

            # get base_file_nodes__ids by file_versions__ids above via the BaseFileVersionsThrough model
            base_file_versions_set = BaseFileVersionsThrough.objects.filter(fileversion__in=file_versions)
            base_file_nodes__ids = base_file_versions_set.values_list('basefilenode_id', flat=True).distinct('basefilenode_id')

            # get base_file_nodes
            base_file_nodes = BaseFileNode.objects.filter(
                id__in=base_file_nodes__ids,
                target_object_id__in=projects__ids,
            ).exclude(
                # exclude deleted files
                Q(deleted__isnull=False) | Q(deleted_on__isnull=False) | Q(deleted_by_id__isnull=False),
            )
        else:
            # Add-on storage: get base_file_nodes based on type, provider name and project ids
            base_file_nodes = BaseFileNode.objects.filter(
                type=f'osf.{self.destination.provider_name}file',
                provider=self.destination.provider_name,
                target_object_id__in=projects__ids,
                _materialized_path__isnull=False,
            ).exclude(
                # exclude deleted files
                Q(deleted__isnull=False) | Q(deleted_on__isnull=False) | Q(deleted_by_id__isnull=False),
            )

        total_size = 0
        total_file = 0
        files = []
        # get file information
        for file in base_file_nodes:
            file_provider = file.provider
            file_info = {
                'id': file.id,
                'guid': file.get_guid()._id if file.get_guid() is not None else None,
                'path': file.path,
                'materialized_path': file.materialized_path,
                'name': file.name,
                'provider': file_provider,
                'created_at': file.created.strftime('%Y-%m-%d %H:%M:%S'),
                'modified_at': file.modified.strftime('%Y-%m-%d %H:%M:%S'),
                'project': {},
                'tags': [],
                'version': [],
                'size': 0,
                'location': {},
                'timestamp': {},
                'checkout_id': file.checkout_id or None,
            }

            # project
            project = file.target
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
                project_id=file.target._id, file_id=file._id).first()
            if timestamp:
                timestamp_info = {
                    'timestamp_id': timestamp.id,
                    'inspection_result_status': timestamp.inspection_result_status,
                    'provider': timestamp.provider,
                    'upload_file_modified_user': timestamp.upload_file_modified_user,
                    'project_id': timestamp.project_id,
                    'path': timestamp.path,
                    'key_file_name': timestamp.key_file_name,
                    'upload_file_created_user': timestamp.upload_file_created_user,
                    'upload_file_size': timestamp.upload_file_size,
                    'verify_file_size': timestamp.verify_file_size,
                    'verify_user': timestamp.verify_user,
                }
                file_info['timestamp'] = timestamp_info

            if file_provider == 'osfstorage':
                # file versions
                file_versions = file.versions.order_by('-created')
                file_versions_info = []
                for version in file_versions:
                    file_version_thru = version.get_basefilenode_version(file)
                    version_info = {
                        'identifier': version.identifier,
                        'created_at': version.created.strftime('%Y-%m-%d %H:%M:%S'),
                        'modified_at': version.modified.strftime('%Y-%m-%d %H:%M:%S'),
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
                if file_versions_info:
                    file_info['size'] = file_versions_info[-1]['size']
                    file_info['location'] = file_versions_info[-1]['location']
            else:
                file_version_url = waterbutler_api_url_for(
                    file.target._id, file_provider, file.path, _internal=True, versions='', **kwargs
                )
                file_versions_res = requests.get(file_version_url)
                if file_versions_res.status_code != 200:
                    continue

                # Get file versions
                file_versions = file_versions_res.json().get('data', [])
                file_versions_info = []

                for version in file_versions:
                    version_attributes = version.get('attributes', {})
                    version_identifier = version_attributes.get('version')
                    version_info = {
                        'identifier': version_identifier,
                        'contributor': '',  # External storage does not store who really uploaded file
                        'location': {},
                    }

                    # Get metadata with file version
                    metadata_url = waterbutler_api_url_for(
                        file.target._id, file_provider, file.path, _internal=True, meta='', version=version_identifier, **kwargs
                    )
                    metadata_res = requests.get(metadata_url)
                    if metadata_res.status_code != 200:
                        continue

                    metadata_data = metadata_res.json().get('data', {})
                    metadata_attributes = metadata_data.get('attributes', {})
                    metadata_extra = metadata_attributes.get('extra', {})

                    sha256 = get_hashes_from_metadata(file_provider, metadata_extra, 'sha256')
                    md5 = get_hashes_from_metadata(file_provider, metadata_extra, 'md5')
                    sha1 = get_hashes_from_metadata(file_provider, metadata_extra, 'sha1')
                    sha512 = get_hashes_from_metadata(file_provider, metadata_extra, 'sha512')
                    if sha256 is not None:
                        metadata_attributes['sha256'] = sha256
                    if md5 is not None:
                        metadata_attributes['md5'] = md5
                    if sha1 is not None:
                        metadata_attributes['sha1'] = sha1
                    if sha512 is not None:
                        metadata_attributes['sha512'] = sha512
                    version_info['version_name'] = metadata_attributes.get('name', file.name)
                    version_info['created_at'] = metadata_attributes.get('created_utc')
                    version_info['size'] = metadata_attributes.get('sizeInt')
                    version_info['modified_at'] = metadata_attributes.get('modified_utc', metadata_attributes.get('modified'))
                    if file_provider == 'onedrivebusiness':
                        # Get quick XOR hash
                        quick_xor_hash = get_hashes_from_metadata(file_provider, metadata_extra, 'quickXorHash')
                        metadata_attributes['quickXorHash'] = quick_xor_hash
                        # OneDrive Business does not keep old version info in metadata API, get some info from version API instead
                        version_extra = version_attributes.get('extra', {})
                        version_info['metadata'] = metadata_attributes
                        version_info['size'] = version_extra.get('size')
                        version_info['modified_at'] = version_attributes.get('modified_utc', version_attributes.get('modified'))
                    version_info['metadata'] = metadata_attributes

                    total_file += 1
                    total_size += version_info['size']
                    file_versions_info.append(version_info)

                file_info['version'] = file_versions_info
                if file_versions_info:
                    file_info['size'] = file_versions_info[-1]['size']
                    file_info['location'] = file_versions_info[-1]['location']
            files.append(file_info)

        file_info_json['folders'] = folders
        file_info_json['files'] = files

        export_data_json['files_numb'] = total_file
        export_data_json['size'] = total_size
        export_data_json['projects_numb'] = len(projects__ids)

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
