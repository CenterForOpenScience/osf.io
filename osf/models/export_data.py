from __future__ import unicode_literals

import logging
import os.path
import hashlib

import requests
from django.db import models
from django.db.models import DateTimeField

from addons.osfstorage.models import Region
from api.base.utils import waterbutler_api_url_for
from osf.models import (
    base,
    BaseFileNode,
    BaseFileVersionsThrough,
    ExportDataLocation,
    Institution,
    RdmFileTimestamptokenVerifyResult,
    FileVersion,
    AbstractNode,
)
from admin.base import settings as admin_settings
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import EncryptedJSONField
from website.settings import INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD

logger = logging.getLogger(__name__)

__all__ = [
    'DateTruncMixin',
    'SecondDateTimeField',
    'ExportData',
    'get_hashes_from_metadata'
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


def get_hashes_from_metadata(provider_name, extra, hash_name):
    """ Get hash value from extra value in metadata"""
    value = extra.get(hash_name)
    extra_hashes = extra.get('hashes', {})
    if not value:
        # Try to get hash value by hash name in extra
        value = extra_hashes.get(hash_name)

    if not value:
        extra_provider_value = extra_hashes.get(provider_name)
        if hash_name == 'sha256' and provider_name == 'dropboxbusiness':
            # Dropbox Business: get sha256 from extra
            value = extra_provider_value
        elif type(extra_provider_value) is dict:
            # Other: try to get hash value by hash name in extra[<provider_name>]
            value = extra_provider_value.get(hash_name)

    return value


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
    EXPORT_DATA_AVAILABLE = [STATUS_COMPLETED, STATUS_CHECKING]
    EXPORT_DATA_FILES_FOLDER = 'files'
    EXPORT_DATA_FAKE_NODE_ID = 'export_location'

    source = models.ForeignKey(Region, on_delete=models.CASCADE)
    location = models.ForeignKey(ExportDataLocation, on_delete=models.CASCADE)
    process_start = SecondDateTimeField(auto_now=False, auto_now_add=True)
    process_end = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    last_check = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    status = models.CharField(choices=EXPORT_DATA_STATUS_CHOICES, max_length=255)
    export_file = models.CharField(max_length=255, null=True, blank=True)
    project_number = models.PositiveIntegerField(default=0)
    file_number = models.PositiveIntegerField(default=0)
    total_size = models.BigIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    task_id = models.CharField(max_length=255, null=True, blank=True)
    creator = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    source_name = models.CharField(max_length=200, null=True, blank=True)
    source_waterbutler_credentials = EncryptedJSONField(default=dict, null=True, blank=True)
    source_waterbutler_settings = DateTimeAwareJSONField(default=dict, null=True, blank=True)
    class Meta:
        db_table = 'osf_export_data'
        unique_together = ('source', 'location', 'process_start')

    def __repr__(self):
        return f'"({self.source}-{self.location})[{self.status}]"'

    __str__ = __repr__

    def extract_file_information_json_from_source_storage(self, **kwargs):
        # Get region guid == institution guid
        source_storage_guid = self.source.guid
        # Get Institution by guid
        institution = Institution.load(source_storage_guid)

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
                'name': self.source.name,
                'type': self.source.provider_full_name,
            },
            'projects_numb': self.project_number,
            'files_numb': self.file_number,
            'size': self.total_size,
            'file_path': self.get_file_info_file_path(),
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
        # If source is not NII storage, only get projects that belongs to that source institutional storage
        if self.source.provider_name != 'osfstorage' and self.source.id != 1:
            projects__ids = projects.filter(addons_osfstorage_node_settings__region=self.source).values_list('id', flat=True)

        # get folder nodes
        base_folder_nodes = BaseFileNode.objects.filter(
            # type='osf.{}folder'.format(self.source.provider_short_name),
            type__endswith='folder',
            target_object_id__in=projects__ids,
            deleted=None)
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

        if self.source.provider_name in INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD:
            # Bulk-mount storage
            # If source is NII storage, also get default storage
            if self.source.provider_name == 'osfstorage' and self.source.id != 1:
                # get list FileVersion linked to source storage, default storage
                # but the creator must be affiliated with current institution
                file_versions = FileVersion.objects.filter(region_id__in=[1, self.source.id], creator__affiliated_institutions___id=source_storage_guid)
            else:
                # get list FileVersion linked to source storage
                file_versions = self.source.fileversion_set.all()
                # but the creator must be affiliated with current institution
                file_versions = file_versions.filter(creator__affiliated_institutions___id=source_storage_guid)

            # get base_file_nodes__ids by file_versions__ids above via the BaseFileVersionsThrough model
            base_file_versions_set = BaseFileVersionsThrough.objects.filter(fileversion__in=file_versions)
            base_file_nodes__ids = base_file_versions_set.values_list('basefilenode_id', flat=True).distinct('basefilenode_id')

            # get base_file_nodes
            base_file_nodes = BaseFileNode.objects.filter(
                id__in=base_file_nodes__ids,
                target_object_id__in=projects__ids,
                deleted=None)
        else:
            # Add-on storage: get base_file_nodes based on type, provider name and project ids
            base_file_nodes = BaseFileNode.objects.filter(
                type=f'osf.{self.source.provider_name}file',
                provider=self.source.provider_name,
                target_object_id__in=projects__ids,
                deleted=None)

        total_size = 0
        total_file = 0
        files = []
        # get file information
        for file in base_file_nodes:
            file_provider = file.provider
            file_info = {
                'id': file.id,
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

    def get_source_file_versions_min(self, file_info_json):
        file_versions = []
        for file in file_info_json.get('files', []):
            project_id = file.get('project').get('id')
            provider = file.get('provider')
            file_path = file.get('path')
            versions = file.get('version', [])
            file_id = file.get('id')
            for index, version in enumerate(versions):
                identifier = version.get('identifier')
                modified_at = version.get('modified_at')
                if identifier == 'null' and provider == 'ociinstitutions':
                    # OCI for Institutions: fix download error if version is latest
                    identifier = None
                if index == 0 and provider == 'nextcloudinstitutions':
                    # Nextcloud for Institutions: fix download error if version is latest
                    identifier = None
                metadata = version.get('metadata')
                # get metadata.get('sha256', metadata.get('md5', metadata.get('sha512', metadata.get('sha1', metadata.get('name')))))
                file_name = metadata.get('sha256', metadata.get('md5', metadata.get('sha512', metadata.get('sha1'))))
                if provider == 'onedrivebusiness':
                    # OneDrive Business: get new hash based on quickXorHash and file version modified time
                    quick_xor_hash = metadata.get('quickXorHash')
                    new_string_to_hash = f'{quick_xor_hash}{modified_at}'
                    file_name = hashlib.sha256(new_string_to_hash.encode('utf-8')).hexdigest()
                file_versions.append((project_id, provider, file_path, identifier, file_name, file_id,))

        return file_versions

    @property
    def process_start_timestamp(self):
        return self.process_start.strftime('%s')

    @property
    def process_start_display(self):
        return self.process_start.strftime('%Y%m%dT%H%M%S')

    @property
    def export_data_folder_name(self):
        """export_{source.id}_{process_start_timestamp} folder for each export process"""
        return f'export_{self.source.id}_{self.process_start_timestamp}'

    def create_export_data_folder(self, cookies, **kwargs):
        """Create export_{source.id}_{process_start_timestamp} folder on the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
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
        """Delete export_{source.id}_{process_start_timestamp} folder and sub-files on the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.export_data_folder_path
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            confirm_delete=1,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.delete(url, cookies=cookies)

    @property
    def export_data_folder_path(self):
        """export_{source.id}_{process_start_timestamp} folder path for each export data"""
        return f'/export_{self.source.id}_{self.process_start_timestamp}/'

    @property
    def export_data_temp_file_path(self):
        """/tmp/_export_{source.id}_{process_start_timestamp}.json as temporary file"""
        return os.path.join(admin_settings.TEMPORARY_PATH, '_' + self.export_data_folder_name + '.json')

    def get_export_data_filename(self, institution_guid=None):
        """get export_data_{institution_guid}_{process_start_timestamp}.json file name for each institution"""
        if not institution_guid:
            institution_guid = self.source.guid
        return f'export_data_{institution_guid}_{self.process_start_timestamp}.json'

    def upload_export_data_file(self, cookies, file_path, **kwargs):
        """Upload export_{source.id}_{process_start_timestamp}/export_data_{institution_guid}_{process_start_timestamp}.json file
           to the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.export_data_folder_path
        file_name = kwargs.get('file_name', self.get_export_data_filename(self.location.institution_guid))
        with open(file_path, 'rb') as fp:
            url = waterbutler_api_url_for(
                node_id, provider, path=path,
                name=file_name,
                kind='file',
                _internal=True, location_id=self.location.id,
                **kwargs
            )
            return requests.put(url, data=fp, cookies=cookies)

    def get_export_data_file_path(self, institution_guid=None):
        """get /export_{source.id}_{process_start_timestamp}/export_data_{institution_guid}_{process_start_timestamp}.json file path"""
        if not institution_guid:
            institution_guid = self.source.guid
        return os.path.join('/', self.export_data_folder_name, self.get_export_data_filename(institution_guid))

    def read_export_data_from_location(self, cookies, **kwargs):
        """Get content of /export_{source.id}_{process_start_timestamp}/export_data_{institution_guid}_{process_start_timestamp}.json file
           from the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.get_export_data_file_path(self.location.institution_guid)
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.get(url, cookies=cookies, stream=True)

    def delete_export_data_file_from_location(self, cookies, **kwargs):
        """Delete /export_{source.id}_{process_start_timestamp}/export_data_{institution_guid}_{process_start_timestamp}.json file
           from the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.get_export_data_file_path(self.location.institution_guid)
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.delete(url, cookies=cookies)

    def get_file_info_filename(self, institution_guid=None):
        """get file_info_{institution_guid}_{process_start_timestamp}.json file name for each institution"""
        if not institution_guid:
            institution_guid = self.source.guid
        return f'file_info_{institution_guid}_{self.process_start_timestamp}.json'

    def upload_file_info_file(self, cookies, file_path, **kwargs):
        """Upload export_{source.id}_{process_start_timestamp}/file_info_{institution_guid}_{process_start_timestamp}.json file
           to the storage location"""
        file_name = self.get_file_info_filename(self.location.institution_guid)
        kwargs.setdefault('file_name', file_name)
        return self.upload_export_data_file(cookies, file_path, **kwargs)

    def get_file_info_file_path(self, institution_guid=None):
        """get /export_{source.id}_{process_start_timestamp}/file_info_{institution_guid}_{process_start_timestamp}.json file path"""
        if not institution_guid:
            institution_guid = self.source.guid
        return os.path.join('/', self.export_data_folder_name, self.get_file_info_filename(institution_guid))

    def read_file_info_from_location(self, cookies, **kwargs):
        """Get content of /export_{source.id}_{process_start_timestamp}/file_info_{institution_guid}_{process_start_timestamp}.json file
           from the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.get_file_info_file_path(self.location.institution_guid)
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.get(url, cookies=cookies, stream=True)

    def delete_file_info_file_from_location(self, cookies, **kwargs):
        """Delete /export_{source.id}_{process_start_timestamp}/file_info_{institution_guid}_{process_start_timestamp}.json file
           from the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.get_file_info_file_path(self.location.institution_guid)
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.delete(url, cookies=cookies)

    @property
    def export_data_files_folder_path(self):
        """get /export_{source.id}_{process_start_timestamp}/files/ folder path"""
        return f'/export_{self.source.id}_{self.process_start_timestamp}/{self.EXPORT_DATA_FILES_FOLDER}/'

    def create_export_data_files_folder(self, cookies, **kwargs):
        """Create export_{source.id}_{process_start_timestamp}/files/ folder on the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.export_data_folder_path
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            name=self.EXPORT_DATA_FILES_FOLDER,
            kind='folder', meta='',
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.put(url, cookies=cookies)

    def read_data_file_from_source(self, cookies, project_id, provider, file_path, **kwargs):
        """Get data file from the source storage"""
        url = waterbutler_api_url_for(
            project_id, provider, path=file_path,
            _internal=True,
            **kwargs
        )
        return requests.get(url, cookies=cookies, stream=True)

    def transfer_export_data_file_to_location(self, cookies, file_name, file_data, **kwargs):
        """Upload data file to the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.export_data_files_folder_path
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            name=file_name,
            kind='file',
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.put(url, data=file_data, cookies=cookies)

    def copy_export_data_file_to_location(self, cookies, source_project_id, source_provider, source_file_path, file_name, **kwargs):
        """Copy data file from source storage to the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        location_provider = self.location.provider_name
        path = self.export_data_files_folder_path

        copy_file_url = waterbutler_api_url_for(
            source_project_id, source_provider, path=source_file_path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )

        request_body = {
            'action': 'copy',
            'path': path,
            'conflict': 'warn',
            'rename': file_name,
            'resource': node_id,
            'provider': location_provider
        }

        return requests.post(copy_file_url,
                             headers={'content-type': 'application/json'},
                             cookies=cookies,
                             json=request_body)

    def get_data_file_file_path(self, file_name):
        """get /export_{source.id}_{process_start_timestamp}/files/{file_name} file path"""
        return os.path.join('/', self.export_data_files_folder_path, file_name)

    def read_data_file_from_location(self, cookies, file_name, **kwargs):
        """Get data file from the storage location"""
        node_id = self.EXPORT_DATA_FAKE_NODE_ID
        provider = self.location.provider_name
        path = self.get_data_file_file_path(file_name)
        url = waterbutler_api_url_for(
            node_id, provider, path=path,
            _internal=True, location_id=self.location.id,
            **kwargs
        )
        return requests.get(url, cookies=cookies, stream=True)

    def get_all_restored(self):
        return self.exportdatarestore_set.filter(status__in=self.EXPORT_DATA_AVAILABLE)

    def has_restored(self):
        return self.get_all_restored().exists()

    def get_latest_restored(self):
        return self.get_all_restored().latest('process_end')

    def get_latest_restored_data_with_destination_id(self, destination_id):
        return self.get_all_restored().filter(destination_id=destination_id).latest('process_end')
