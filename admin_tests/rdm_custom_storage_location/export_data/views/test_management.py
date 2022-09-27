import mock
import pytest
from django.core.exceptions import SuspiciousOperation
from django.http import Http404, JsonResponse
from django.test import RequestFactory
from django.urls import reverse
from nose import tools as nt

from admin.rdm_custom_storage_location.export_data.views import management
from admin_tests.utilities import setup_view
from osf.models import ExportData, ExportDataRestore
from osf_tests.factories import AuthUserFactory, ExportDataRestoreFactory
from osf_tests.factories import (
    InstitutionFactory,
    ExportDataFactory,
    RegionFactory,
)
from tests.base import AdminTestCase

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


@pytest.mark.feature_202210
class TestExportBaseView(AdminTestCase):
    def setUp(self):
        super(TestExportBaseView, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = management.ExportBaseView()
        self.view.request = self.request
        self.view.kwargs = {}

    def test_load_institution(self):
        response = self.view.load_institution()
        nt.assert_equal(response, None)


@pytest.mark.feature_202210
class TestMethodGetExportData(AdminTestCase):
    def setUp(self):
        super(TestMethodGetExportData, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()
        self.export_data.save()

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    def test_method(self, mock_export_data):
        mock_export_data.filter.return_value = self.export_data.objects
        mock_export_data.order_by.return_value = [self.export_data]
        res = management.get_export_data(self.institution._id, check_delete=False)
        nt.assert_is_instance(res, list)


@pytest.mark.feature_202210
class TestExportDataListView(AdminTestCase):
    def setUp(self):
        super(TestExportDataListView, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.region._id = self.institution._id
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.institution.save()
        self.region.save()
        self.view = management.ExportDataListView()
        self.request = RequestFactory().get('/fake_path')
        self.request.GET = {'location_id': 1, 'storage_id': 1}
        self.request.user = self.user
        self.view = setup_view(self.view,
                               self.request,
                               institution_id=self.institution.id)

    def test_get(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        mock_render = mock.MagicMock()
        mock_render.return_value = None

        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportBaseView', mock_class):
            with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                res = self.view.get(self.request)
                nt.assert_equal(res, None)


@pytest.mark.feature_202210
class TestExportDataDeletedListView(AdminTestCase):
    def setUp(self):
        super(TestExportDataDeletedListView, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.view = management.ExportDataDeletedListView()
        self.institution = InstitutionFactory()
        self.request = RequestFactory().get(
            reverse('custom_storage_location:export_data:export_data_deleted_list'))
        self.request.user = self.user
        self.view = setup_view(self.view,
                               self.request)

    def test_get(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        mock_render = mock.MagicMock()
        mock_render.return_value = None

        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportBaseView', mock_class):
            with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                res = self.view.get(self.request)
                nt.assert_equal(res, None)


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

    def test_get_not_found(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=0)
        with self.assertRaises(Http404):
            view.get(request)


@pytest.mark.feature_202210
class TestCheckExportData(AdminTestCase):
    def setUp(self):
        super(TestCheckExportData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()

    def test_export_data_not_completed(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        export_data = self.export_data
        export_data.status = 'Checking'
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            res = view.get(request, data_id=export_data.id)
        nt.assert_equal(res.status_code, 400)

    def test_cannot_connect_to_storage(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=400)
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    def test_validate_fail(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = FakeRes(200)
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'extract_file_information_json_from_source_storage')
    def test_check_export_data_successful(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'

        def side_effect():
            return '', FAKE_DATA_NEW

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        mock_request.get.return_value = FakeRes(200)
        self.export_data.source.guid = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
                    res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 200)


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

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    def test_restore_data_with_status_not_completed_and_get_from_request(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}
        export_data = self.export_data
        export_data.status = 'Checking'

        def side_effect(destination_id=100):
            return export_data

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            res = view.get(request, data_id=export_data.id)
        nt.assert_equal(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored')
    def test_restore_data_not_completed_and_not_from_request(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        export_data = self.export_data
        export_data.status = 'Checking'

        def side_effect(destination_id=100):
            return export_data

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            res = view.get(request, data_id=export_data.id)
        nt.assert_equal(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    def test_check_restore_data_cannot_connect_to_storage(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}
        export_data = self.export_data

        def side_effect(destination_id=100):
            return self.export_data_restore

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=400)
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    def test_check_restore_data_with_validate_fail(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}

        def side_effect(destination_id=100):
            return self.export_data_restore

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = FakeRes(200)
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    @mock.patch.object(ExportDataRestore, 'extract_file_information_json_from_destination_storage')
    def test_check_restore_data_successful(self, mock_class_export, mock_class_restore):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}

        def side_effect_export_data():
            return '', FAKE_DATA_NEW

        def side_effect_export_data_restore(destination_id=100):
            return self.export_data_restore

        mock_class_export.side_effect = side_effect_export_data
        mock_class_restore.side_effect = side_effect_export_data_restore
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        mock_request.get.return_value = FakeRes(200)
        self.export_data.source.guid = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
                    res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 200)


@pytest.mark.feature_202210
class TestExportDataFileCSVView(AdminTestCase):
    def setUp(self):
        super(TestExportDataFileCSVView, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.view = management.ExportDataFileCSVView()

    def test_get(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        view = setup_view(self.view, request)
        res = view.get(request)
        nt.assert_equal(res.status_code, 200)


@pytest.mark.feature_202210
class TestDeleteExportDataView(AdminTestCase):
    def setUp(self):
        super(TestDeleteExportDataView, self).setUp()
        self.user = AuthUserFactory()
        self.export_data = ExportDataFactory()
        self.institution = InstitutionFactory()
        self.view = management.DeleteExportDataView()

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently_fail(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=400)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on'}
        view = setup_view(self.view, request)
        with self.assertRaises(SuspiciousOperation):
            view.post(request)

    def test_delete_not_permanently(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)


@pytest.mark.feature_202210
class TestRevertExportData(AdminTestCase):
    def setUp(self):
        super(TestRevertExportData, self).setUp()
        self.user = AuthUserFactory()
        self.view = management.RevertExportDataView()

    def test_post(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)
