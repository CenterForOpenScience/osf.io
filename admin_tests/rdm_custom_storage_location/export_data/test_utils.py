import json

import mock
import pytest
import requests
from django.core.exceptions import SuspiciousOperation
from django.test import RequestFactory
from jsonschema import ValidationError, SchemaError
from mock import patch, MagicMock
from nose import tools as nt
from requests import ConnectionError
from rest_framework import status

from addons.nextcloudinstitutions.models import NextcloudInstitutionsProvider
from admin.rdm_custom_storage_location.export_data import utils
from admin.rdm_custom_storage_location.export_data.views import management
from admin.rdm_custom_storage_location.export_data.views.restore import ProcessError
from admin_tests.utilities import setup_view
from framework.celery_tasks import app as celery_app
from osf.models import ExportData
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExportDataLocationFactory,
    ExportDataFactory,
    ExportDataRestoreFactory,
)
from tests.base import AdminTestCase

FAKE_TASK_ID = '00000000-0000-0000-0000-000000000000'
RESTORE_EXPORT_DATA_PATH = 'admin.rdm_custom_storage_location.export_data.views.restore'
EXPORT_DATA_UTIL_PATH = 'admin.rdm_custom_storage_location.export_data.utils'
EXPORT_DATA_TASK_PATH = 'admin.rdm_custom_storage_location.tasks'
TEST_PROJECT_ID = 'test1'
TEST_PROVIDER = 'osfstorage'
FAKE_DATA = {
    'institution': {
        'id': 66,
        'guid': 'wustl',
        'name': 'Washington University in St. Louis [Test]'
    },
    'files': [
        {
            'id': 10,
            'path': '/631879ebb71d8f1ae01f4c20',
            'materialized_path': '/nii/ember-img/root.png',
            'name': 'root.png',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': '33cca',
                'name': 'Project B0001'
            },
            'tags': ['image', 'png'],
            'version': [
                {
                    'identifier': '1',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 1220,
                    'version_name': 'root.png',
                    'contributor': 'user10@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 1220,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 1220,
                        'modified': 'Fri, 12 Aug 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b33',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 1220,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
        {
            'id': 100,
            'path': '/631879ebb71d8f1a2931920',
            'materialized_path': '/nii/ember-animated/data.txt',
            'name': 'data.txt',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': 'bc56a',
                'name': 'Project B0002'
            },
            'tags': ['txt', 'file'],
            'version': [
                {
                    'identifier': '1',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 100,
                    'version_name': 'data.txt',
                    'contributor': 'user001@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 100,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 100,
                        'modified': 'Fri, 12 Aug 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 100,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
        {
            'id': 1733,
            'path': '/631879ebb71d8f1ae01f4c10',
            'materialized_path': '/nii/ember-animated/-private/sprite.d.ts',
            'name': 'sprite.d.ts',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': 'wh6za',
                'name': 'Project C0001'
            },
            'tags': [],
            'version': [
                {
                    'identifier': '1',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 150,
                    'version_name': 'sprite.d.ts',
                    'contributor': 'user001@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 150,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 150,
                        'modified': 'Fri, 12 Aug 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 150,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
    ]
}

FAKE_DATA_NEW = {
    'institution': {
        'id': 66,
        'guid': 'wustl',
        'name': 'Washington University in St. Louis [Test]'
    },
    'files': [
        {
            'id': 10,
            'path': '/631879ebb71d8f1ae01f4c20',
            'materialized_path': '/nii/ember-img/root.png',
            'name': 'root.png',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': '33cca',
                'name': 'Project B0001'
            },
            'tags': ['image', 'png'],
            'version': [
                {
                    'identifier': '1',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 1220,
                    'version_name': 'root.png',
                    'contributor': 'user10@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 1220,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 1220,
                        'modified': 'Fri, 12 Aug 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b33',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 1220,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
        {
            'id': 100,
            'path': '/631879ebb71d8f1a2931920',
            'materialized_path': '/nii/ember-animated/data.txt',
            'name': 'data.txt',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': 'bc56a',
                'name': 'Project B0002'
            },
            'tags': ['txt', 'file'],
            'version': [
                {
                    'identifier': '2',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 100,
                    'version_name': 'data.txt',
                    'contributor': 'user001@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 100,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 100,
                        'modified': 'Fri, 12 Aug 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 100,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
        {
            'id': 1733,
            'path': '/631879ebb71d8f1ae01f4c10',
            'materialized_path': '/nii/ember-animated/-private/sprite.d.ts',
            'name': 'sprite.d.ts',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': 'wh6za',
                'name': 'Project C0001'
            },
            'tags': [],
            'version': [
                {
                    'identifier': '1',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 150,
                    'version_name': 'sprite.ds.ts',
                    'contributor': 'user002@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 150,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 150,
                        'modified': 'Fri, 10 Oct 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
                {
                    'identifier': '2',
                    'created_at': '2022-010-07 11:00:00',
                    'size': 2250,
                    'version_name': 'sprite.d.ts',
                    'contributor': 'user001@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '3f4e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 2250,
                        'extra': {},
                        'sha256': 'f6dbb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '77662617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 2250,
                        'modified': 'Fri, 20 Oct 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'modified_utc': '2022-10-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 2250,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
    ]
}


class FakeRes:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        data = FAKE_DATA
        return data


def mock_check_not_aborted_task():
    return None


def mock_check_aborted_task():
    raise ProcessError('Mock test exception by aborting task')


def get_mock_get_file_data_response_addon_storage(*args, **kwargs):
    response_body = {'data': []}
    if args[2] == '/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/folder/',
                        'materialized': '/folder/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/file2.txt',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }
    elif args[2] == '/folder/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/folder/file1.txt',
                        'materialized': '/folder/file1.txt',
                        'kind': 'file'
                    }
                }
            ]
        }
    elif args[2] == '/test_exception/':
        raise ConnectionError('Mock test connection error while getting file info')

    test_response = requests.Response()
    test_response.status_code = status.HTTP_200_OK if args[2] != '/test_error_response/' else status.HTTP_404_NOT_FOUND
    test_response._content = json.dumps(response_body).encode('utf-8')
    return test_response


def get_mock_file_data_response_bulk_mount(*args, **kwargs):
    if args[2] == '/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/fake_folder_id/',
                        'materialized': '/folder/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/fake_file2_id',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }
    elif args[2] == '/fake_folder_id/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/fake_file1_id',
                        'materialized': '/folder/file1.txt',
                        'kind': 'file'
                    }
                }
            ]
        }

    test_response = requests.Response()
    test_response.status_code = status.HTTP_200_OK
    test_response._content = json.dumps(response_body).encode('utf-8')
    return test_response


@pytest.mark.feature_202210
class TestUtils(AdminTestCase):

    def setUp(self):
        self.institution = InstitutionFactory()

        self.access_key = 'access_key'
        self.secret_key = 'secret_key'
        self.bucket = 'mybucket'

        self.wb_credentials = {
            'storage': {
                'access_key': self.access_key,
                'secret_key': self.secret_key,
            }
        }

        self.wb_settings = {
            'storage': {
                'folder': '/code/website/osfstoragecache',
                'provider': 'filesystem',
            }
        }

    def test_write_json_file__successfully(self):
        mock_json_dump_patcher = mock.patch(f'{EXPORT_DATA_UTIL_PATH}.json.dump')
        json_data = {'json_data': 'json_data'}
        output_file = '_temp.json'

        mock_json_dump = mock_json_dump_patcher.start()

        utils.write_json_file(json_data, output_file)
        call_args = mock_json_dump.call_args
        mock_json_dump.assert_called()
        nt.assert_equal(call_args[0][0], json_data)
        nt.assert_equal(call_args[1], {'ensure_ascii': False, 'indent': 2, 'sort_keys': False})

        mock_json_dump_patcher.stop()

    def test_from_json__file_not_found(self):
        mock_json_dump_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.json.dump',
            side_effect=Exception()
        )
        json_data = {'json_data': 'json_data'}
        output_file = '_temp.json'

        mock_json_dump = mock_json_dump_patcher.start()
        with pytest.raises(Exception):
            utils.write_json_file(json_data, output_file)
        mock_json_dump.assert_called()

        mock_json_dump_patcher.stop()

    def test_update_storage_location__create_new(self):
        result = utils.update_storage_location(
            institution_guid=self.institution.guid,
            storage_name='testname',
            wb_credentials=self.wb_credentials,
            wb_settings=self.wb_settings,
        )
        nt.assert_equal(result.waterbutler_credentials, self.wb_credentials)
        nt.assert_equal(result.waterbutler_settings, self.wb_settings)
        nt.assert_equal(result.name, 'testname')

    def test_update_storage_location__update(self):
        ExportDataLocationFactory(
            institution_guid=self.institution.guid,
            name='testname',
            waterbutler_credentials={'storage': {}},
            waterbutler_settings={'storage': {}},
        )
        result = utils.update_storage_location(
            institution_guid=self.institution.guid,
            storage_name='testname',
            wb_credentials=self.wb_credentials,
            wb_settings=self.wb_settings,
        )
        nt.assert_not_equal(result.waterbutler_credentials, {'storage': {}})
        nt.assert_not_equal(result.waterbutler_settings, {'storage': {}})
        nt.assert_equal(result.waterbutler_credentials, self.wb_credentials)
        nt.assert_equal(result.waterbutler_settings, self.wb_settings)
        nt.assert_equal(result.name, 'testname')

    def test_test_dropboxbusiness_connection__no_option(self):
        mock_get_two_addon_options = mock.MagicMock(return_value=None)
        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options', mock_get_two_addon_options):
            data, status_code = utils.test_dropboxbusiness_connection(self.institution)
            mock_get_two_addon_options.assert_called()
            nt.assert_equal(status_code, 400)
            nt.assert_true('message' in data)
            nt.assert_equal(data.get('message'), 'Invalid Institution ID.: {}'.format(self.institution.id))

    def test_test_dropboxbusiness_connection__no_token(self):
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value=None
        )

        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()

        data, status_code = utils.test_dropboxbusiness_connection(self.institution)
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_equal(status_code, 400)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'No tokens.')

        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()

    def test_test_dropboxbusiness_connection__valid(self):
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            return_value=True
        )

        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()

        data, status_code = utils.test_dropboxbusiness_connection(self.institution)
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Credentials are valid')

        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()

    def test_test_dropboxbusiness_connection__invalid_token(self):
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            side_effect=Exception()
        )

        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()

        data, status_code = utils.test_dropboxbusiness_connection(self.institution)
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_equal(status_code, 400)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Invalid tokens.')

        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()

    def test_save_s3_credentials__error_connection(self):
        mock_test_s3_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3_connection = mock_test_s3_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3_connection.assert_called()
        mock_update_storage_location.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_test_s3_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_s3_credentials__successfully(self):
        mock_test_s3_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3_connection = mock_test_s3_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3_connection.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(data, {'message': 'Saved credentials successfully!!'})
        nt.assert_equal(status_code, 200)

        mock_test_s3_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_s3compat_credentials__error_connection(self):
        mock_test_s3compat_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3compat_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3compat_connection = mock_test_s3compat_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3compat_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            host_url='http://host_url/',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3compat_connection.assert_called()
        mock_update_storage_location.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_test_s3compat_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_s3compat_credentials__successfully(self):
        mock_test_s3compat_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3compat_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3compat_connection = mock_test_s3compat_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3compat_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            host_url='http://host_url/',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3compat_connection.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(data, {'message': 'Saved credentials successfully!!'})
        nt.assert_equal(status_code, 200)

        mock_test_s3compat_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_dropboxbusiness_credentials__error_connection(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()

        data, status_code = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__no_option(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()

        ret = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_called()
        nt.assert_is_none(ret)

        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__no_token(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()

        ret = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_is_none(ret)

        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__valid(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=(mock.MagicMock(), mock.MagicMock())
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            return_value=mock.Mock(team_folders=mock.Mock(keys=mock.Mock(return_value=['team_folder_id'])))
        )
        mock_get_current_admin_group_and_sync_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_current_admin_group_and_sync',
            return_value=('admin_group', 'admin_dbmid_list')
        )

        mock_get_current_admin_dbmid_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_current_admin_dbmid',
            return_value='admin_dbmid'
        )
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()
        mock_get_current_admin_group_and_sync = mock_get_current_admin_group_and_sync_patcher.start()
        mock_get_current_admin_dbmid = mock_get_current_admin_dbmid_patcher.start()
        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        mock_get_current_admin_group_and_sync.assert_called()
        mock_get_current_admin_dbmid.assert_called()
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Dropbox Business was set successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()
        mock_get_current_admin_dbmid_patcher.stop()
        mock_get_current_admin_group_and_sync_patcher.stop()
        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__invalid_token(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            side_effect=Exception()
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()

        with pytest.raises(Exception):
            utils.save_dropboxbusiness_credentials(
                institution=self.institution,
                storage_name='testname',
                provider_name='dropboxbusiness',
            )
            mock_test_dropboxbusiness_connection.assert_called()
            mock_get_two_addon_options.assert_called()
            mock_addon_option_to_token.assert_called()

        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_basic_storage_institutions_credentials_common__no_extended_data(self):
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )
        provider = NextcloudInstitutionsProvider(username='username', password='password', host='host')

        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_basic_storage_institutions_credentials_common(
            institution=self.institution,
            storage_name='test_storage_name',
            folder='test_folder/',
            provider_name='test_provider_name',
            provider=provider,
        )
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Saved credentials successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()

    def test_save_basic_storage_institutions_credentials_common__with_extended_data(self):
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )
        provider = NextcloudInstitutionsProvider(username='username', password='password', host='host')

        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_basic_storage_institutions_credentials_common(
            institution=self.institution,
            storage_name='test_storage_name',
            folder='test_folder/',
            provider_name='test_provider_name',
            provider=provider,
            extended_data={'year': 1964},
        )
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Saved credentials successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()

    def test_save_nextcloudinstitutions_credentials__error_connection(self):
        mock_test_owncloud_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_owncloud_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_save_basic_storage_institutions_credentials_common_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.save_basic_storage_institutions_credentials_common',
            return_value=({'message': 'test'}, 400)
        )

        mock_test_owncloud_connection = mock_test_owncloud_connection_patcher.start()
        mock_save_basic_storage_institutions_credentials_common = mock_save_basic_storage_institutions_credentials_common_patcher.start()

        data, status_code = utils.save_nextcloudinstitutions_credentials(
            institution=self.institution,
            storage_name='test_storage_name',
            host_url='test_url',
            username='test_username',
            password='test_password',
            folder='test_folder/',
            notification_secret='not_secret',
            provider_name='nextcloudinstitutions',
        )
        mock_test_owncloud_connection.assert_called()
        mock_save_basic_storage_institutions_credentials_common.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_save_basic_storage_institutions_credentials_common_patcher.stop()
        mock_test_owncloud_connection_patcher.stop()

    def test_save_nextcloudinstitutions_credentials__successfully(self):
        mock_test_owncloud_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_owncloud_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_owncloud_connection = mock_test_owncloud_connection_patcher.start()
        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_nextcloudinstitutions_credentials(
            institution=self.institution,
            storage_name='test_storage_name',
            host_url='test_url',
            username='test_username',
            password='test_password',
            folder='test_folder/',
            notification_secret='not_secret',
            provider_name='nextcloudinstitutions',
        )
        mock_test_owncloud_connection.assert_called()
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Saved credentials successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()
        mock_test_owncloud_connection_patcher.stop()


@pytest.mark.feature_202210
class TestExportDataInformationView(AdminTestCase):
    def setUp(self):
        super(TestExportDataInformationView, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.view = management.ExportDataInformationView()
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()

    def test_get_success(self):
        mock_render = mock.MagicMock()
        mock_render.return_value = None
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        mock_request = mock.MagicMock()
        fake_res = FakeRes(200)
        mock_request.get.return_value = fake_res
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                    res = view.get(request)
                    nt.assert_equal(res, None)

    @mock.patch('osf.models.export_data.requests')
    def test_get_file_info_not_valid(self, mock_request):
        fake_res = FakeRes(200)
        mock_request.get.return_value = fake_res
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=self.export_data.id)
        with self.assertRaises(SuspiciousOperation):
            view.get(request)


@pytest.mark.feature_202210
class TestCheckExportData(AdminTestCase):
    def setUp(self):
        super(TestCheckExportData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()

    def test_count_file_ng_ok(self):
        data_old = utils.process_data_information(FAKE_DATA['files'])
        data_new = utils.process_data_information(FAKE_DATA_NEW['files'])
        rs = utils.count_files_ng_ok(data_new, data_old)
        nt.assert_greater(rs['ng'], 0)

    def test_validate_exported_data(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.return_value = None

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_exported_data({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_true(result)

    def test_validate_exported_data_validation_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = ValidationError(f'Mock test jsonschema.ValidationError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_exported_data({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_false(result)

    def test_validate_exported_data_other_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = FileNotFoundError(f'Mock test jsonschema.SchemaError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                with nt.assert_raises(FileNotFoundError):
                    result = utils.validate_exported_data({}, 'fake-schema.json')
                    mock_from_json.assert_called()
                    mock_validate.assert_called()
                    nt.assert_is_none(result)

    def test_check_diff(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 3
            }

        }
        utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])

    def test_check_diff_epsilon(self):
        res = utils.deep_diff(1.2, 2.1, parent_key='section1', epsilon_keys=['section1', 'section2'])
        nt.assert_equal(res, None)

    def test_check_diff_between_list_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_standard, a_new, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_check_diff_between_list_not_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_type_dict(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section3': {
                'category1': 1,
                'category2': 2
            },
            'section4': {
                'category1': 1,
                'category2': 3
            }

        }
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)


@pytest.mark.feature_202210
class TestCheckRestoreData(AdminTestCase):
    def setUp(self):
        super(TestCheckRestoreData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()
        self.export_data_restore = ExportDataRestoreFactory()
        self.export_data_restore.export = self.export_data

    def test_count_file_ng_ok(self):
        data_old = utils.process_data_information(FAKE_DATA['files'])
        data_new = utils.process_data_information(FAKE_DATA_NEW['files'])
        rs = utils.count_files_ng_ok(data_new, data_old)
        nt.assert_greater(rs['ng'], 0)

    def test_check_diff(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 3
            }

        }
        utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])

    def test_check_diff_epsilon(self):
        res = utils.deep_diff(1.2, 2.1, parent_key='section1', epsilon_keys=['section1', 'section2'])
        nt.assert_equal(res, None)

    def test_check_diff_between_list_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_standard, a_new, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_check_diff_between_list_not_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_check_diff_between_dict(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section3': {
                'category1': 1,
                'category2': 2
            },
            'section4': {
                'category1': 1,
                'category2': 3
            }

        }
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)


@pytest.mark.feature_202210
class TestUtilsForRestoreData(AdminTestCase):
    def setUp(self):
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })
        self.export_data = ExportDataFactory()
        self.export_data_restore = ExportDataRestoreFactory(status=ExportData.STATUS_RUNNING)
        self.destination_id = self.export_data_restore.destination.id

    # check_for_any_running_restore_process
    def test_check_for_any_running_restore_process_true_result(self):
        result = utils.check_for_any_running_restore_process(self.destination_id)
        nt.assert_equal(result, True)

    def test_check_for_any_running_restore_process_false_result(self):
        result = utils.check_for_any_running_restore_process(-1)
        nt.assert_equal(result, False)

    # validate_file_json
    def test_validate_file_json(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.return_value = None

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_file_json({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_true(result)

    def test_validate_file_json_validation_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = ValidationError(f'Mock test jsonschema.ValidationError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_file_json({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_false(result)

    def test_validate_file_json_schema_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = SchemaError(f'Mock test jsonschema.SchemaError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_file_json({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_false(result)

    def test_validate_file_json_other_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = FileNotFoundError(f'Mock test jsonschema.SchemaError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                with nt.assert_raises(FileNotFoundError):
                    result = utils.validate_file_json({}, 'fake-schema.json')
                    mock_from_json.assert_called()
                    mock_validate.assert_called()
                    nt.assert_is_none(result)

    # get_file_data
    def test_get_file_data(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(TEST_PROJECT_ID, TEST_PROVIDER, '/test/file.txt', None)
            mock_get.assert_called()
            nt.assert_equal(response.content, b'{}')
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_file_data_info(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = {}

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(TEST_PROJECT_ID, TEST_PROVIDER, '/test/file.txt', None,
                                           get_file_info=True)
            mock_get.assert_called()
            nt.assert_equal(response.content, {})
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_file_data_with_version(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(TEST_PROJECT_ID, TEST_PROVIDER, '/test/file.txt', None, version=2)
            mock_get.assert_called()
            nt.assert_equal(response.content, b'{}')
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_file_data_from_export_data(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(ExportData.EXPORT_DATA_FAKE_NODE_ID, TEST_PROVIDER, '/test/file.txt',
                                           None,
                                           location_id=self.export_data.location.id)
            mock_get.assert_called()
            nt.assert_equal(response.content, b'{}')
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    # create_folder
    def test_create_folder(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_201_CREATED
        test_response._content = json.dumps({}).encode('utf-8')

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.create_folder(TEST_PROJECT_ID, TEST_PROVIDER, '/', 'test/', None)
            nt.assert_equal(response_body, {})
            nt.assert_equal(status_code, status.HTTP_201_CREATED)

    def test_create_folder_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_409_CONFLICT

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.create_folder(TEST_PROJECT_ID, TEST_PROVIDER, '/', 'test/', None)
            nt.assert_is_none(response_body)
            nt.assert_equal(status_code, status.HTTP_409_CONFLICT)

    def test_create_folder_exception(self):
        mock_put = MagicMock()
        mock_put.side_effect = ConnectionError('Mock test in create folder on storage')
        with patch('requests.put', mock_put):
            response_body, status_code = utils.create_folder(TEST_PROJECT_ID, TEST_PROVIDER, '/', 'test/', None)
            nt.assert_is_none(response_body)
            nt.assert_is_none(status_code)

    # upload_file
    def test_upload_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_201_CREATED
        test_response._content = json.dumps({}).encode('utf-8')

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.upload_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {}, 'test.txt',
                                                           None)
            nt.assert_equal(response_body, {})
            nt.assert_equal(status_code, status.HTTP_201_CREATED)

    def test_upload_file_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_409_CONFLICT

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.upload_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {}, 'test.txt',
                                                           None)
            nt.assert_is_none(response_body)
            nt.assert_equal(status_code, status.HTTP_409_CONFLICT)

    def test_upload_file_exception(self):
        mock_put = MagicMock()
        mock_put.side_effect = ConnectionError('Mock test in upload file on storage')

        with patch('requests.put', mock_put):
            response_body, status_code = utils.upload_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {}, 'test.txt',
                                                           None)
            nt.assert_is_none(response_body)
            nt.assert_is_none(status_code)

    # update_existing_file
    def test_update_existing_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.update_existing_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {},
                                                                    'test.txt',
                                                                    None)
            nt.assert_equal(response_body, {})
            nt.assert_equal(status_code, status.HTTP_200_OK)

    def test_update_existing_file_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_404_NOT_FOUND

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.update_existing_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {},
                                                                    'test.txt',
                                                                    None)
            nt.assert_is_none(response_body)
            nt.assert_equal(status_code, status.HTTP_404_NOT_FOUND)

    def test_update_existing_file_exception(self):
        mock_put = MagicMock()
        mock_put.side_effect = ConnectionError('Mock test in update existing file on storage')

        with patch('requests.put', mock_put):
            response_body, status_code = utils.update_existing_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {},
                                                                    'test.txt',
                                                                    None)
            nt.assert_is_none(response_body)
            nt.assert_is_none(status_code)

    # create_folder_path
    def test_create_folder_path_invalid_folder_path(self):
        response = utils.create_folder_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder', None)
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_create_folders(self, mock_get_file_data, mock_create_folder):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_failed_to_get_folder_info(self, mock_get_file_data, mock_create_folder):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_not_found_response = requests.Response()
        test_not_found_response.status_code = status.HTTP_404_NOT_FOUND

        mock_get_file_data.return_value = test_not_found_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_no_match_folder_info(self, mock_get_file_data, mock_create_folder):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder2/',
                            'materialized': '/folder2/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_create_folder_with_existing_folder(self, mock_get_file_data, mock_create_folder):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder/',
                            'materialized': '/folder/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_not_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_failed_to_create_folder(self, mock_get_file_data, mock_create_folder):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (None, status.HTTP_400_BAD_REQUEST)

        response = utils.create_folder_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    # upload_file_path
    def test_upload_file_path_invalid_file_path(self):
        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', {}, None)
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_create_folders_and_file(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_failed_to_get_folder_info(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_not_found_response = requests.Response()
        test_not_found_response.status_code = status.HTTP_404_NOT_FOUND

        mock_get_file_data.return_value = test_not_found_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_no_match_folder_info(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder2/',
                            'materialized': '/folder2/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_create_file_with_existing_folder(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder/',
                            'materialized': '/folder/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_not_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.update_existing_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_update_file(self, mock_get_file_data, mock_create_folder, mock_upload_file, mock_update_file):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder/',
                            'materialized': '/folder/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({
                    'data': [{
                        'attributes': {
                            'path': '/folder/file.txt',
                            'materialized': '/folder/file.txt'
                        }
                    }]
                }).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        update_file_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/file.txt',
                    'materialized': '/folder/file.txt'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)
        mock_update_file.return_value = (update_file_response_body, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_not_called()
        mock_update_file.assert_called()
        mock_upload_file.assert_not_called()
        nt.assert_equal(response, update_file_response_body)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_failed_to_create_folder(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (None, status.HTTP_400_BAD_REQUEST)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_not_called()
        nt.assert_equal(response, {})

    # move_file
    def test_move_file_in_addon_storage(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_post = MagicMock()
        mock_post.return_value = test_response
        with patch('requests.post', mock_post):
            response = utils.move_file(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file1.txt',
                                       '/backup/folder/file1.txt',
                                       None, is_addon_storage=True)
            nt.assert_equal(response.status_code, status.HTTP_200_OK)
            nt.assert_is_none(response.content)

    def test_move_file_in_bulk_mount_storage(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_post = MagicMock()
        mock_post.return_value = test_response
        with patch('requests.post', mock_post):
            response = utils.move_file(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', '/hash_backup_folder_id/',
                                       None,
                                       is_addon_storage=False)
            nt.assert_equal(response.status_code, status.HTTP_200_OK)
            nt.assert_is_none(response.content)

    def test_move_file_exception(self):
        mock_post = MagicMock()
        mock_post.side_effect = ConnectionError('Mock test exception for moving folder or file')
        with patch('requests.post', mock_post):
            with nt.assert_raises(ConnectionError):
                response = utils.move_file(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file1.txt',
                                           '/backup/folder/file1.txt',
                                           None, is_addon_storage=True)
                nt.assert_is_none(response)

    # move_addon_folder_to_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_success(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_called()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_aborted(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        with nt.assert_raises(ProcessError):
            result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                       self.export_data_restore.process_start_timestamp,
                                                       None,
                                                       check_abort_task=mock_check_aborted_task)
            mock_get_all_paths.assert_called()
            mock_move_file.assert_not_called()
            mock_delete_paths.assert_not_called()
            nt.assert_is_none(result)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_empty_path_list(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_paths.return_value = ([], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_move_files_error(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file'

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None,
                                                   check_abort_task=mock_check_not_aborted_task)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result,
                        {'error': f'{status.HTTP_500_INTERNAL_SERVER_ERROR} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_exception(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file.'

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.side_effect = Exception(f'Mock test exception when move file')
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None,
                                                   check_abort_task=mock_check_not_aborted_task)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': repr(Exception('Mock test exception when move file'))})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_exception_and_aborted(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file'

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.side_effect = Exception('Mock test exception when move file')
        mock_delete_paths.return_value = None

        with nt.assert_raises(ProcessError):
            result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                       self.export_data_restore.process_start_timestamp,
                                                       None,
                                                       check_abort_task=mock_check_aborted_task)
            mock_get_all_paths.assert_called()
            mock_move_file.assert_called()
            mock_delete_paths.assert_not_called()
            nt.assert_is_none(result)

    # get_all_file_paths_in_addon_storage
    def test_get_all_file_paths_in_addon_storage(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/folder/file1.txt', '/file2.txt'])
            nt.assert_equal(root_child_folders, ['/folder/'])

    def test_get_all_file_paths_in_addon_storage_exclude_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None,
                                                                                           exclude_path_regex='^\\/folder\\/.*$')
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/file2.txt'])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_include_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None,
                                                                                           include_path_regex='^\\/folder\\/.*$')
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/folder/file1.txt'])
            nt.assert_equal(root_child_folders, ['/folder/'])

    def test_get_all_file_paths_in_addon_storage_response_error(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/test_error_response/',
                                                                                           None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, [])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_empty_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/empty_path/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/empty_path/'])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_invalid_regex(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None,
                                                                                           exclude_path_regex='\\/folder_[0-9]++\\/.*')
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, [])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_exception(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/test_exception/',
                                                                                           None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, [])
            nt.assert_equal(root_child_folders, [])

    # move_bulk_mount_folder_to_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_success(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_empty_path_list(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_not_called()
        mock_move_file.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_abort_while_creating_folder(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_process_error = ProcessError('Mock test exception by aborting task')
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None,
                                                        check_abort_task=mock_check_aborted_task)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_not_called()
        mock_move_file.assert_not_called()
        nt.assert_equal(result, {'error': repr(test_process_error)})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_abort_while_moving_file(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        abort_flag = False

        def side_effect_after_create_folder(*args, **kwargs):
            nonlocal abort_flag
            abort_flag = True
            return create_folder_response, status.HTTP_201_CREATED

        def mock_check_task():
            if abort_flag:
                mock_check_aborted_task()
            else:
                mock_check_not_aborted_task()

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.side_effect = side_effect_after_create_folder
        mock_move_file.return_value = test_response

        with nt.assert_raises(ProcessError):
            result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                            self.export_data_restore.process_start_timestamp,
                                                            None,
                                                            check_abort_task=mock_check_task)
            mock_get_all_child_paths.assert_called()
            mock_create_folder.assert_called()
            mock_move_file.assert_not_called()
            nt.assert_is_none(result)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_response_error_while_creating_folder(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = {}, status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_not_called()
        nt.assert_equal(result, {'error': 'Cannot create backup folder'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_response_error_while_moving_file(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file'
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_called()
        nt.assert_equal(result,
                        {'error': f'{status.HTTP_500_INTERNAL_SERVER_ERROR} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_exception_while_moving_file(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        connection_error = ConnectionError(f'Mock test exception while moving file')

        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.side_effect = connection_error

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_called()
        nt.assert_equal(result, {'error': repr(connection_error)})

    # get_all_child_paths_in_bulk_mount_storage
    def test_get_all_child_paths_in_bulk_mount_storage_invalid_path(self):
        mock_get_file_data = MagicMock()
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/file.txt', None)
            mock_get_file_data.assert_not_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_at_root(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_folder_id/', '/folder/'), ('/fake_file2_id', '/file2.txt')])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_at_root_child_folder(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_file1_id', '/folder/file1.txt')])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_response_error(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data = MagicMock()
        mock_get_file_data.return_value = test_response
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/test_error_response/',
                                                                                        None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_exception(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = ConnectionError('Mock test connection error while getting file info')
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/test_exception/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_exclude_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/', None,
                                                                                        exclude_path_regex='^\\/folder\\/$')
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_file2_id', '/file2.txt')])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_and_get_encrypted_path_from_args(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder/', None,
                                                                                        get_path_from='/folder/')
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_file1_id', '/folder/file1.txt')])
            nt.assert_equal(path_from_args, '/fake_folder_id/')

    def test_get_all_child_paths_in_bulk_mount_storage_non_existing_data_in_root_child_folder(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder3/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_non_existing_data_in_deepest_folder(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder/folder4/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_invalid_exclude_regex(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/', None,
                                                                                        exclude_path_regex='^\\/folder_[0-9]++\\/$')
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    # move_addon_folder_from_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup(self, mock_get_all_file_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = (['/backup_2022101010/folder/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_empty_path_list(self, mock_get_all_file_paths, mock_move_file,
                                                           mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = ([], [])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_response_error(self, mock_get_all_file_paths, mock_move_file,
                                                          mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_403_FORBIDDEN
        test_response._content = b'Mock test error response while moving file'

        mock_get_all_file_paths.return_value = (['/backup_2022101010/folder/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': f'{status.HTTP_403_FORBIDDEN} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_exception(self, mock_get_all_file_paths, mock_move_file, mock_delete_paths):
        connection_error = ConnectionError('Mock test exception while moving file')

        mock_get_all_file_paths.return_value = (['/backup_2022101010/folder/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.side_effect = connection_error
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': repr(connection_error)})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_only_file_in_backup_folder(self, mock_get_all_file_paths, mock_move_file,
                                                                      mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = (['/backup_2022101010/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_no_backup_folder(self, mock_get_all_file_paths, mock_move_file,
                                                            mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = (['/folder/file1.txt', '/file2.txt'],
                                                [])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    # move_bulk_mount_folder_from_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup(self, mock_get_all_child_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = ([('/backup_child_folder_id/', '/backup_2022101010/folder/'),
                                                  ('/backup_file2_id', '/backup_2022101010/file2.txt')],
                                                 '/backup_folder_id/')
        mock_move_file.return_value = test_response
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        nt.assert_equal(mock_move_file.call_count, 2)
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup_empty_path_list(self, mock_get_all_child_paths, mock_move_file,
                                                                mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = ([], None)
        mock_move_file.return_value = test_response
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup_response_error(self, mock_get_all_child_paths, mock_move_file,
                                                               mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_403_FORBIDDEN
        test_response._content = b'Mock test error response while moving file'

        mock_get_all_child_paths.return_value = ([('/backup_child_folder_id/', '/backup_2022101010/folder/'),
                                                  ('/backup_file2_id', '/backup_2022101010/file2.txt')],
                                                 '/backup_folder_id/')
        mock_move_file.return_value = test_response
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': f'{status.HTTP_403_FORBIDDEN} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup_exception(self, mock_get_all_child_paths, mock_move_file,
                                                          mock_delete_paths):
        connection_error = ConnectionError('Mock test exception while moving file')

        mock_get_all_child_paths.return_value = ([('/backup_child_folder_id/', '/backup_2022101010/folder/'),
                                                  ('/backup_file2_id', '/backup_2022101010/file2.txt')],
                                                 '/backup_folder_id/')
        mock_move_file.side_effect = connection_error
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': repr(connection_error)})

    # delete_paths
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    def test_delete_paths(self, mock_delete_file):
        mock_delete_file.return_value = None
        utils.delete_paths(TEST_PROJECT_ID, TEST_PROVIDER, ['/folder/', '/file.txt'], None)
        nt.assert_equal(mock_delete_file.call_count, 2)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    def test_delete_paths_exception(self, mock_delete_file):
        mock_delete_file.side_effect = ConnectionError(f'Mock test exception while deleting file')
        utils.delete_paths(TEST_PROJECT_ID, TEST_PROVIDER, ['/folder/', '/file.txt'], None)
        nt.assert_equal(mock_delete_file.call_count, 2)

    # delete_file
    @patch(f'requests.delete')
    def test_delete_file(self, mock_delete_request):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_delete_request.return_value = test_response
        response = utils.delete_file(TEST_PROJECT_ID, TEST_PROVIDER, '/file.txt', None)
        mock_delete_request.assert_called_once()
        nt.assert_equal(response, test_response)

    # delete_all_files_except_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup(self, mock_get_file_data, mock_delete_file):
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        nt.assert_equal(mock_delete_file.call_count, 2)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_get_file_response_error(self, mock_get_file_data, mock_delete_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_404_NOT_FOUND

        mock_get_file_data.return_value = test_response
        with nt.assert_raises(Exception):
            utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
            mock_get_file_data.assert_called_once()
            mock_delete_file.assert_not_called()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_get_file_exception(self, mock_get_file_data, mock_delete_file):
        mock_get_file_data.side_effect = ConnectionError('Mock test exception while getting file data')
        with nt.assert_raises(ConnectionError):
            utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
            mock_get_file_data.assert_called_once()
            mock_delete_file.assert_not_called()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_no_paths_to_delete(self, mock_get_file_data, mock_delete_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({'data': []}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        mock_delete_file.assert_not_called()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_with_backup_folders(self, mock_get_file_data, mock_delete_file):
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/backup_2022101010/',
                        'materialized': '/backup_2022101010/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/file2.txt',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }

        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps(response_body).encode('utf-8')

        mock_get_file_data.return_value = test_response
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        mock_delete_file.assert_called_once()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_delete_file_exception(self, mock_get_file_data, mock_delete_file):
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage
        mock_delete_file.side_effect = ConnectionError('Mock test exception while deleting path')
        with nt.assert_raises(ConnectionError):
            utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
            mock_get_file_data.assert_called_once()
            mock_delete_file.assert_called_once()

    @patch(f're.compile')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_invalid_regex(self, mock_get_file_data, mock_delete_file,
                                                          mock_compile_regex):
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/backup_2022101010/',
                        'materialized': '/backup_2022101010/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/file2.txt',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }

        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps(response_body).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_compile_regex.side_effect = ValueError('Mock test invalid regex')
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        nt.assert_equal(mock_delete_file.call_count, 2)

    # is_add_on_storage
    def test_is_add_on_storage(self):
        # missing provider
        nt.assert_is_none(utils.is_add_on_storage(None))
        nt.assert_is_none(utils.is_add_on_storage('osf_storage'))

        # both addon method and bulk-mount method
        nt.assert_true(utils.is_add_on_storage('owncloud'))
        nt.assert_true(utils.is_add_on_storage('s3compat'))
        nt.assert_true(utils.is_add_on_storage('s3'))

        # only addon method providers
        nt.assert_true(utils.is_add_on_storage('nextcloudinstitutions'))
        nt.assert_true(utils.is_add_on_storage('s3compatinstitutions'))
        nt.assert_true(utils.is_add_on_storage('ociinstitutions'))
        nt.assert_true(utils.is_add_on_storage('dropboxbusiness'))

        # only bulk-mount method providers
        nt.assert_false(utils.is_add_on_storage('onedrivebusiness'))
        nt.assert_false(utils.is_add_on_storage('swift'))
        nt.assert_false(utils.is_add_on_storage('box'))
        nt.assert_false(utils.is_add_on_storage('nextcloud'))
        nt.assert_false(utils.is_add_on_storage('osfstorage'))
        nt.assert_false(utils.is_add_on_storage('onedrive'))
        nt.assert_false(utils.is_add_on_storage('googledrive'))
