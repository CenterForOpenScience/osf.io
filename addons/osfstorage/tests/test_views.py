import json
from unittest import mock
import datetime

import pytest
import responses
from waffle.testutils import override_flag
from dateutil.parser import parse as parse_datetime
from website import settings

from addons.github.tests.factories import GitHubAccountFactory
from addons.github.models import GithubFile
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from framework.auth.core import Auth
from addons.osfstorage.tests.utils import (
    StorageTestCase, Delta, AssertDeltas,
    recursively_create_file,
)
from addons.osfstorage.tests import factories
from addons.osfstorage.tests.utils import make_payload

from framework.auth import signing
from website.util import rubeus, api_url_for
from framework.auth import cas

from osf import features
from osf.models import Tag, QuickFilesNode
from osf.models import files as models
from addons.osfstorage.apps import osf_storage_root
from addons.osfstorage import utils
from addons.base.views import make_auth, addon_view_file
from addons.osfstorage import settings as storage_settings
from api_tests.utils import create_test_file, create_test_preprint_file
from api.caching.settings import STORAGE_USAGE_KEY
from api.caching.utils import storage_usage_cache

from osf_tests.factories import ProjectFactory, ApiOAuth2PersonalTokenFactory, PreprintFactory
from website.files.utils import attach_versions
from website.settings import EXTERNAL_EMBER_APPS
from api_tests.draft_nodes.views.test_draft_node_files_lists import prepare_mock_wb_response


def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    record = node_settings.get_root().append_file(path)
    record.add_version(version)
    record.save()
    return record


@pytest.mark.django_db
class HookTestCase(StorageTestCase):

    def send_hook(self, view_name, view_kwargs, payload, target, method='get', **kwargs):
        guid = view_kwargs.pop('guid', None) or target._id
        signed_data = signing.sign_data(signing.default_signer, payload)
        if method == 'get':
            view_kwargs |= signed_data
        else:
            kwargs['json'] = signed_data
        method = getattr(self.app, method)
        return method(
            api_url_for(view_name, guid=guid, **view_kwargs),
            **kwargs
        )


@pytest.mark.django_db
class TestGetMetadataHook(HookTestCase):

    def test_empty(self):
        res = self.send_hook(
            'osfstorage_get_children',
            {'fid': self.node_settings.get_root()._id, 'user_id': self.user._id},
            {},
            self.node
        )
        assert isinstance(res.json, list)
        assert res.json == []

    def test_file_metdata(self):
        path = 'kind/of/magíc.mp3'
        record = recursively_create_file(self.node_settings, path)
        version = factories.FileVersionFactory()
        record.add_version(version)
        record.save()
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': record.parent._id},
            {},
            self.node
        )
        assert isinstance(res.json, dict)
        assert res.json == record.parent.serialize(True)

    def test_preprint_primary_file_metadata(self):
        preprint = PreprintFactory()
        record = preprint.primary_file
        version = factories.FileVersionFactory()
        record.add_version(version)
        record.save()
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': record.parent._id},
            {},
            preprint
        )
        assert isinstance(res.json, dict)
        assert res.json == record.parent.serialize(True)

    def test_children_metadata(self):
        path = 'kind/of/magíc.mp3'
        record = recursively_create_file(self.node_settings, path)
        version = factories.FileVersionFactory()
        record.add_version(version)
        record.save()
        res = self.send_hook(
            'osfstorage_get_children',
            {'fid': record.parent._id, 'user_id': self.user._id},
            {},
            self.node
        )
        assert len(res.json) == 1
        res_data = res.json[0]
        expected_data = record.serialize()

        # Datetimes in response might not be exactly the same as in record.serialize
        # because of the way Postgres serializes dates. For example,
        # '2017-06-05T17:32:20.964950+00:00' will be
        # serialized as '2017-06-05T17:32:20.96495+00:00' by postgres
        # Therefore, we parse the dates then compare them
        expected_date_modified = parse_datetime(expected_data.pop('modified'))
        expected_date_created = parse_datetime(expected_data.pop('created'))

        res_date_modified = parse_datetime(res_data.pop('modified'))
        res_date_created = parse_datetime(res_data.pop('created'))

        # latestVersionSeen should not be present in record.serialize, because it has to do
        # with the user making the request itself, which isn't important when serializing the record
        expected_data['latestVersionSeen'] = None

        assert res_date_modified == expected_date_modified
        assert res_date_created == expected_date_created
        assert res_data == expected_data

    def test_children_metadata_preprint(self):
        preprint = PreprintFactory()
        record = preprint.primary_file
        version = factories.FileVersionFactory()
        record.add_version(version)
        record.save()
        res = self.send_hook(
            'osfstorage_get_children',
            {'fid': record.parent._id, 'user_id': self.user._id},
            {},
            preprint
        )
        assert len(res.json) == 1
        res_data = res.json[0]
        expected_data = record.serialize()

        # Datetimes in response might not be exactly the same as in record.serialize
        # because of the way Postgres serializes dates. For example,
        # '2017-06-05T17:32:20.964950+00:00' will be
        # serialized as '2017-06-05T17:32:20.96495+00:00' by postgres
        # Therefore, we parse the dates then compare them
        expected_date_modified = parse_datetime(expected_data.pop('modified'))
        expected_date_created = parse_datetime(expected_data.pop('created'))

        res_date_modified = parse_datetime(res_data.pop('modified'))
        res_date_created = parse_datetime(res_data.pop('created'))

        # latestVersionSeen should not be present in record.serialize, because it has to do
        # with the user making the request itself, which isn't important when serializing the record
        expected_data['latestVersionSeen'] = None

        assert res_date_modified == expected_date_modified
        assert res_date_created == expected_date_created

    def test_osf_storage_root(self):
        auth = Auth(self.project.creator)
        result = osf_storage_root(self.node_settings.config, self.node_settings, auth)
        node = self.project
        expected = rubeus.build_addon_root(
            node_settings=self.node_settings,
            name='',
            permissions=auth,
            user=auth.user,
            nodeUrl=node.url,
            nodeApiUrl=node.api_url,
        )
        root = result[0]
        assert root == expected

    def test_root_default(self):
        res = self.send_hook('osfstorage_get_metadata', {}, {}, self.node)

        assert res.json['fullPath'] == '/'
        assert res.json['id'] == self.node_settings.get_root()._id

    def test_root_preprint_default(self):
        preprint = PreprintFactory()
        res = self.send_hook('osfstorage_get_metadata', {}, {}, preprint)

        assert res.json['fullPath'] == '/'
        assert res.json['id'] == preprint.root_folder._id

    def test_metadata_not_found(self):
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': 'somebogusid'}, {},
            self.node,
        )
        assert res.status_code == 404

    def test_metadata_not_found_lots_of_slashes(self):
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': '/not/fo/u/nd/'}, {},
            self.node,
        )
        assert res.status_code == 302
        assert '/login?service=' in res.location

        self.node.is_public = True
        self.node.save()
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': '/not/fo/u/nd/'}, {},
            self.node,
        )
        assert res.status_code == 404


@pytest.mark.django_db
class TestGetStorageQuotaHook(HookTestCase):
    def test_no_storage_use(self):
        res = self.send_hook(
            'osfstorage_get_storage_quota_status',
            {'guid': self.node._id},
            payload={},
            target=None,
            method='get'
        )
        assert res.status_code == 200
        assert not res.json['over_quota']

    def test_under_quota_storage_use(self):
        key = STORAGE_USAGE_KEY.format(target_id=self.node._id)
        storage_usage_cache.set(key, (settings.STORAGE_LIMIT_PRIVATE - 1) * settings.GBs, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        res = self.send_hook(
            'osfstorage_get_storage_quota_status',
            {'guid': self.node._id},
            payload={},
            target=None,
            method='get'
        )
        assert res.status_code == 200
        assert not res.json['over_quota']

    def test_over_quota_storage_use(self):
        key = STORAGE_USAGE_KEY.format(target_id=self.node._id)
        storage_usage_cache.set(key, (settings.STORAGE_LIMIT_PRIVATE + 1) * settings.GBs, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        res = self.send_hook(
            'osfstorage_get_storage_quota_status',
            {'guid': self.node._id},
            payload={},
            target=None,
            method='get'
        )
        assert res.status_code == 200
        assert res.json['over_quota']

    def test_preprint_storage_use(self):
        preprint = PreprintFactory()
        res = self.send_hook(
            'osfstorage_get_storage_quota_status',
            {'guid': preprint._id},
            payload={},
            target=None,
            method='get'
        )
        assert res.status_code == 200
        assert not res.json['over_quota']

@pytest.mark.django_db
class TestUploadFileHook(HookTestCase):

    def setUp(self):
        super().setUp()
        self.name = 'pízza.png'
        self.record = recursively_create_file(self.node_settings, self.name)
        self.auth = make_auth(self.user)

    def send_upload_hook(self, parent, target=None, payload=None, **kwargs):
        return self.send_hook(
            'osfstorage_create_child',
            {'fid': parent._id},
            payload=payload or {},
            target=target or self.project,
            method='post',
            **kwargs
        )

    def make_payload(self, **kwargs):
        user = kwargs.pop('user', self.user)
        name = kwargs.pop('name', self.name)
        return make_payload(user=user, name=name, **kwargs)

    def test_upload_create(self):
        name = 'slightly-mad'

        res = self.send_upload_hook(self.node_settings.get_root(), self.project, self.make_payload(name=name))

        assert res.status_code == 201
        assert res.json['status'] == 'success'

        record = self.node_settings.get_root().find_child_by_name(name)
        version = models.FileVersion.load(res.json['version'])

        assert version.size == 123
        assert version.location_hash == 'file'

        assert version.location == {
            'object': 'file',
            'uname': 'testmachine',
            'service': 'filesystem',
            'provider': 'filesystem',
            storage_settings.WATERBUTLER_RESOURCE: 'blah',
        }
        assert version.metadata == {
            'size': 123,
            'name': 'file',
            'base64': '==',
            'provider': 'filesystem',
            'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
        }

        assert version is not None
        assert [version] == list(record.versions.all())
        assert version not in self.record.versions.all()
        assert version.get_basefilenode_version(record).version_name == record.name
        assert record.serialize() == res.json['data']
        assert version.get_basefilenode_version(record).version_name == record.name
        assert res.json['data']['downloads'] == self.record.get_download_count()

    def test_upload_update(self):
        delta = Delta(lambda: self.record.versions.count(), lambda value: value + 1)
        with AssertDeltas(delta):
            res = self.send_upload_hook(self.node_settings.get_root(), self.project, self.make_payload())
            self.record.reload()
        assert res.status_code == 200
        assert res.json['status'] == 'success'
        version = models.FileVersion.load(res.json['version'])
        assert version is not None
        assert version in self.record.versions.all()

    def test_upload_duplicate(self):
        location = {
            'service': 'cloud',
            storage_settings.WATERBUTLER_RESOURCE: 'osf',
            'object': 'file',
        }
        version = self.record.create_version(self.user, location)
        with AssertDeltas(Delta(lambda: self.record.versions.count())):
            res = self.send_upload_hook(self.node_settings.get_root(), payload=self.make_payload())
            self.record.reload()
        assert res.status_code == 200
        assert res.json['status'] == 'success'
        version = models.FileVersion.load(res.json['version'])
        assert version is not None
        assert version in self.record.versions.all()

    def test_upload_create_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, payload=self.make_payload(name=name))

        assert res.status_code == 201
        assert res.json['status'] == 'success'
        assert res.json['data']['downloads'] == self.record.get_download_count()

        version = models.FileVersion.load(res.json['version'])

        assert version is not None
        assert version not in self.record.versions.all()

        record = parent.find_child_by_name(name)
        assert version in record.versions.all()
        assert record.name == name
        assert record.versions.first().get_basefilenode_version(record).version_name == name
        assert record.parent == parent

    def test_upload_create_child_with_same_name(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        self.node_settings.get_root().append_file(name)
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, payload=self.make_payload(name=name))

        assert res.status_code == 201
        assert res.json['status'] == 'success'
        assert res.json['data']['downloads'] == self.record.get_download_count()

        version = models.FileVersion.load(res.json['version'])

        assert version is not None
        assert version not in self.record.versions.all()

        record = parent.find_child_by_name(name)
        assert version in record.versions.all()
        assert record.name == name
        assert record.versions.first().get_basefilenode_version(record).version_name == name
        assert record.parent == parent

    def test_upload_fail_to_create_version_due_to_checkout(self):
        user = factories.AuthUserFactory()
        name = 'Gunter\'s noise.mp3'
        self.node_settings.get_root().append_file(name)
        root = self.node_settings.get_root()
        file = root.find_child_by_name(name)
        file.checkout = user
        file.save()
        res = self.send_upload_hook(root, payload=self.make_payload(name=name))

        assert res.status_code == 403

    def test_update_nested_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.get_root().append_folder('cheesey')
        old_node = parent.append_file(name)

        res = self.send_upload_hook(parent, payload=self.make_payload(name=name))

        old_node.reload()
        new_node = parent.find_child_by_name(name)

        assert res.status_code == 200
        assert res.json['status'] == 'success'
        assert res.json['data']['downloads'] == new_node.get_download_count()

        assert old_node == new_node

        version = models.FileVersion.load(res.json['version'])

        assert version is not None
        assert version in new_node.versions.all()

        assert version in new_node.versions.all()
        assert new_node.name == name
        assert new_node.parent == parent

    def test_upload_weird_name(self):
        name = 'another/dir/carpe.png'
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, payload=self.make_payload(name=name))

        assert res.status_code == 400
        assert len(parent.children) == 0

    def test_upload_to_file(self):
        name = 'carpe.png'
        parent = self.node_settings.get_root().append_file('cheesey')
        res = self.send_upload_hook(parent, payload=self.make_payload(name=name))

        assert parent.is_file
        assert res.status_code == 400

    def test_upload_no_data(self):
        res = self.send_upload_hook(self.node_settings.get_root())

        assert res.status_code == 400

    # def test_upload_update_deleted(self):
    #     pass


@pytest.mark.django_db
class TestUploadFileHookPreprint(TestUploadFileHook):

    def setUp(self):
        super().setUp()
        self.preprint = PreprintFactory(creator=self.user)
        self.name = self.preprint.primary_file.name
        self.record = self.preprint.primary_file
        self.auth = make_auth(self.user)

    def test_upload_create(self):
        name = 'slightly-mad'

        res = self.send_upload_hook(self.preprint.root_folder, self.preprint, self.make_payload(name=name))

        assert res.status_code == 201
        assert res.json['status'] == 'success'

        record = self.preprint.root_folder.find_child_by_name(name)
        version = models.FileVersion.load(res.json['version'])

        assert version.size == 123
        assert version.location_hash == 'file'

        assert version.location == {
            'object': 'file',
            'uname': 'testmachine',
            'service': 'filesystem',
            'provider': 'filesystem',
            storage_settings.WATERBUTLER_RESOURCE: 'blah',
        }
        assert version.metadata == {
            'size': 123,
            'name': 'file',
            'base64': '==',
            'provider': 'filesystem',
            'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
        }

        assert version is not None
        assert [version] == list(record.versions.all())
        assert version not in self.record.versions.all()
        assert record.serialize() == res.json['data']
        assert res.json['data']['downloads'] == self.record.get_download_count()

    def test_upload_update(self):
        delta = Delta(lambda: self.record.versions.count(), lambda value: value + 1)
        with AssertDeltas(delta):
            res = self.send_upload_hook(self.preprint.root_folder, self.preprint, self.make_payload())
            self.record.reload()
        assert res.status_code == 200
        assert res.json['status'] == 'success'
        version = models.FileVersion.load(res.json['version'])
        assert version is not None
        assert version in self.record.versions.all()
        assert self.record.versions.first().get_basefilenode_version(self.record).version_name == self.name

    def test_upload_duplicate(self):
        location = {
            'service': 'cloud',
            storage_settings.WATERBUTLER_RESOURCE: 'osf',
            'object': 'file',
        }
        version = self.record.create_version(self.user, location)
        with AssertDeltas(Delta(lambda: self.record.versions.count())):
            res = self.send_upload_hook(self.preprint.root_folder, self.preprint, self.make_payload())
            self.record.reload()
        assert res.status_code == 200
        assert res.json['status'] == 'success'
        version = models.FileVersion.load(res.json['version'])
        assert version is not None
        assert version in self.record.versions.all()

    def test_upload_create_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.preprint.root_folder.append_folder('cheesey')
        res = self.send_upload_hook(parent, self.preprint, self.make_payload(name=name))

        assert res.status_code == 201
        assert res.json['status'] == 'success'
        assert res.json['data']['downloads'] == self.record.get_download_count()

        version = models.FileVersion.load(res.json['version'])

        assert version is not None
        assert version not in self.record.versions.all()

        record = parent.find_child_by_name(name)
        assert version in record.versions.all()
        assert record.name == name
        assert record.parent == parent

    def test_upload_create_child_with_same_name(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        self.preprint.root_folder.append_file(name)
        parent = self.preprint.root_folder.append_folder('cheesey')
        res = self.send_upload_hook(parent, self.preprint, self.make_payload(name=name))

        assert res.status_code == 201
        assert res.json['status'] == 'success'
        assert res.json['data']['downloads'] == self.record.get_download_count()

        version = models.FileVersion.load(res.json['version'])

        assert version is not None
        assert version not in self.record.versions.all()

        record = parent.find_child_by_name(name)
        assert version in record.versions.all()
        assert record.name == name
        assert record.parent == parent

    def test_upload_fail_to_create_version_due_to_checkout(self):
        user = factories.AuthUserFactory()
        name = 'Gunter\'s noise.mp3'
        self.preprint.root_folder.append_file(name)
        root = self.preprint.root_folder
        file = root.find_child_by_name(name)
        file.checkout = user
        file.save()
        res = self.send_upload_hook(root, self.preprint, self.make_payload(name=name))

        assert res.status_code == 403

    def test_update_nested_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.preprint.root_folder.append_folder('cheesey')
        old_node = parent.append_file(name)

        res = self.send_upload_hook(parent, self.preprint, self.make_payload(name=name))

        old_node.reload()
        new_node = parent.find_child_by_name(name)

        assert res.status_code == 200
        assert res.json['status'] == 'success'
        assert res.json['data']['downloads'] == new_node.get_download_count()

        assert old_node == new_node

        version = models.FileVersion.load(res.json['version'])

        assert version is not None
        assert version in new_node.versions.all()

        assert version in new_node.versions.all()
        assert new_node.name == name
        assert new_node.parent == parent

    def test_upload_weird_name(self):
        name = 'another/dir/carpe.png'
        parent = self.preprint.root_folder.append_folder('cheesey')
        res = self.send_upload_hook(parent, self.preprint, self.make_payload(name=name))

        assert res.status_code == 400
        assert len(parent.children) == 0

    def test_upload_to_file(self):
        name = 'carpe.png'
        parent = self.preprint.root_folder.append_file('cheesey')
        res = self.send_upload_hook(parent, self.preprint, self.make_payload(name=name))

        assert parent.is_file
        assert res.status_code == 400

    def test_upload_no_data(self):
        res = self.send_upload_hook(self.preprint.root_folder, self.preprint)

        assert res.status_code == 400


@pytest.mark.django_db
class TestUpdateMetadataHook(HookTestCase):

    def setUp(self):
        super().setUp()
        self.path = 'greasy/pízza.png'
        self.record = recursively_create_file(self.node_settings, self.path)
        self.version = factories.FileVersionFactory()
        self.record.add_version(self.version)
        self.record.save()
        self.payload = {
            'metadata': {
                'size': 123,
                'modified': 'Mon, 16 Feb 2015 18:45:34 GMT',
                'md5': 'askjasdlk;jsadlkjsadf',
                'sha256': 'sahduashduahdushaushda',
            },
            'version': self.version._id,
            'size': 321,  # Just to make sure the field is ignored
        }

    def send_metadata_hook(self, payload=None, target=None, **kwargs):
        return self.send_hook(
            'osfstorage_update_metadata',
            {},
            payload=payload or self.payload,
            target=target or self.node,
            method='put',
            **kwargs
        )

    def test_callback(self):
        self.version.external_modified = None
        self.version.save()
        self.send_metadata_hook()
        self.version.reload()
        #Test fields are added
        assert self.version.metadata['size'] == 123
        assert self.version.metadata['md5'] == 'askjasdlk;jsadlkjsadf'
        assert self.version.metadata['modified'] == 'Mon, 16 Feb 2015 18:45:34 GMT'

        #Test attributes are populated
        assert self.version.size == 123
        assert isinstance(self.version.external_modified, datetime.datetime)

    def test_archived(self):
        self.send_metadata_hook({
            'version': self.version._id,
            'metadata': {
                'vault': 'osf_storage_prod',
                'archive': 'Some really long glacier object id here'
            }
        })
        self.version.reload()

        assert self.version.metadata['vault'] == 'osf_storage_prod'
        assert self.version.metadata['archive'] == 'Some really long glacier object id here'

    def test_archived_record_not_found(self):
        res = self.send_metadata_hook(
            payload={
                'metadata': {'archive': 'glacier'},
                'version': self.version._id[::-1],
                'size': 123,
                'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
            },
        )
        assert res.status_code == 404
        self.version.reload()
        assert 'archive' not in self.version.metadata


@pytest.mark.django_db
class TestUpdateMetadataHookPreprints(HookTestCase):

    def setUp(self):
        super().setUp()
        self.preprint = PreprintFactory()
        self.record = self.preprint.primary_file
        self.path = 'greasy/pízza.png'
        self.version = factories.FileVersionFactory()
        self.record.add_version(self.version)
        self.record.save()
        self.payload = {
            'metadata': {
                'size': 123,
                'modified': 'Mon, 16 Feb 2015 18:45:34 GMT',
                'md5': 'askjasdlk;jsadlkjsadf',
                'sha256': 'sahduashduahdushaushda',
            },
            'version': self.version._id,
            'size': 321,  # Just to make sure the field is ignored
        }

    def send_metadata_hook(self, payload=None, target=None, **kwargs):
        return self.send_hook(
            'osfstorage_update_metadata',
            {},
            payload=payload or self.payload,
            target=target or self.preprint,
            method='put',
            **kwargs
        )

    def test_callback(self):
        self.version.external_modified = None
        self.version.save()
        self.send_metadata_hook()
        self.version.reload()
        #Test fields are added
        assert self.version.metadata['size'] == 123
        assert self.version.metadata['md5'] == 'askjasdlk;jsadlkjsadf'
        assert self.version.metadata['modified'] == 'Mon, 16 Feb 2015 18:45:34 GMT'

        #Test attributes are populated
        assert self.version.size == 123
        assert isinstance(self.version.external_modified, datetime.datetime)

    def test_archived(self):
        self.send_metadata_hook({
            'version': self.version._id,
            'metadata': {
                'vault': 'osf_storage_prod',
                'archive': 'Some really long glacier object id here'
            }
        })
        self.version.reload()

        assert self.version.metadata['vault'] == 'osf_storage_prod'
        assert self.version.metadata['archive'] == 'Some really long glacier object id here'

    def test_archived_record_not_found(self):
        res = self.send_metadata_hook(
            payload={
                'metadata': {'archive': 'glacier'},
                'version': self.version._id[::-1],
                'size': 123,
                'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
            },
        )
        assert res.status_code == 404
        self.version.reload()
        assert 'archive' not in self.version.metadata


@pytest.mark.django_db
class TestGetRevisions(StorageTestCase):

    def setUp(self):
        super().setUp()
        self.path = 'tie/your/mother/down.mp3'
        self.record = recursively_create_file(self.node_settings, self.path)
        attach_versions(self.record, [factories.FileVersionFactory() for __ in range(15)])
        self.record.save()

    def get_revisions(self, fid=None, guid=None, **kwargs):
        return self.app.get(
            api_url_for(
                'osfstorage_get_revisions',
                fid=fid or self.record._id,
                guid=guid or self.project._id,
                **signing.sign_data(signing.default_signer, {})
            ),
            auth=self.user.auth,
            **kwargs
        )

    def test_get_revisions(self):
        res = self.get_revisions()
        expected = [
            utils.serialize_revision(
                self.project,
                self.record,
                version,
                index=self.record.versions.count() - 1 - idx
            )
            for idx, version in enumerate(self.record.versions.all())
        ]

        assert len(res.json['revisions']) == 15
        assert res.json['revisions'] == [x for x in expected]
        assert res.json['revisions'][0]['index'] == 15
        assert res.json['revisions'][-1]['index'] == 1

    def test_get_revisions_path_not_found(self):
        res = self.get_revisions(fid='missing')
        assert res.status_code == 404


@pytest.mark.django_db
class TestCreateFolder(HookTestCase):

    def setUp(self):
        super().setUp()
        self.root_node = self.node_settings.get_root()

    def create_folder(self, name, parent=None, target=None, **kwargs):
        parent = parent or self.node_settings.get_root()
        target = target or self.project

        return self.send_hook(
            'osfstorage_create_child',
            {'fid': parent._id, 'guid': target._id},
            payload={
                'name': name,
                'user': self.user._id,
                'kind': 'folder'
            },
            target=self.project,
            method='post',
            **kwargs
        )

    def test_create_folder(self):
        resp = self.create_folder('name')

        self.root_node.reload()

        assert resp.status_code == 201
        assert len(self.root_node.children) == 1
        assert self.root_node.children[0].serialize() == resp.json['data']

    def test_no_data(self):
        resp = self.send_hook(
            'osfstorage_create_child',
            {'fid': self.root_node._id, 'guid': self.project._id},
            payload={},
            target=self.project,
            method='post',
        )
        assert resp.status_code == 400

    def test_create_with_parent(self):
        resp = self.create_folder('name')

        assert resp.status_code == 201
        assert self.root_node.children.count() == 1
        assert self.root_node.children.all()[0].serialize() == resp.json['data']

        resp = self.create_folder('name', parent=OsfStorageFileNode.load(resp.json['data']['id']))

        assert resp.status_code == 201
        assert self.root_node.children.count() == 1
        assert not self.root_node.children.all()[0].is_file
        assert self.root_node.children.all()[0].children.count() == 1
        assert not self.root_node.children.all()[0].children.all()[0].is_file
        assert self.root_node.children.all()[0].children.all()[0].serialize() == resp.json['data']


@pytest.mark.django_db
class DeleteHook(HookTestCase):

    def setUp(self):
        super().setUp()
        self.root_node = self.node_settings.get_root()

    def send_hook(self, view_name, view_kwargs, payload, target, method='get', **kwargs):
        method = getattr(self.app, method)
        return method(
            '{url}?payload={payload}&signature={signature}'.format(
                url=api_url_for(view_name, guid=target._id, **view_kwargs),
                **signing.sign_data(signing.default_signer, payload)
            ),
            **kwargs
        )

    def delete(self, file_node, **kwargs):
        return self.send_hook(
            'osfstorage_delete',
            {'fid': file_node._id},
            payload={
                'user': self.user._id
            },
            target=self.node,
            method='delete',
            **kwargs
        )


@pytest.mark.django_db
class TestDeleteHookNode(DeleteHook):

    def test_delete(self):
        file = self.root_node.append_file('Newfile')

        resp = self.delete(file)

        assert resp.status_code == 200
        assert resp.json == {'status': 'success'}
        fid = file._id
        del file
        # models.StoredFileNode._clear_object_cache()
        assert OsfStorageFileNode.load(fid) is None
        assert models.TrashedFileNode.load(fid)

    def test_delete_deleted(self):
        file = self.root_node.append_file('Newfile')
        file.delete()

        resp = self.delete(file)

        assert resp.status_code == 404

    def test_cannot_delete_root(self):
        resp = self.delete(self.root_node)

        assert resp.status_code == 400

    def test_attempt_delete_rented_file(self):
        user = factories.AuthUserFactory()
        file_checked = self.root_node.append_file('Newfile')
        file_checked.checkout = user
        file_checked.save()

        res = self.delete(file_checked)
        assert res.status_code == 403

    def test_attempt_delete_folder_with_rented_file(self):
        folder = self.root_node.append_folder('Hotel Events')
        user = factories.AuthUserFactory()
        file_checked = folder.append_file('Checkout time')
        file_checked.checkout = user
        file_checked.save()

        res = self.delete(folder)
        assert res.status_code == 403

    def test_attempt_delete_double_nested_folder_rented_file(self):
        folder = self.root_node.append_folder('One is not enough')
        folder_two = folder.append_folder('Two might be doe')
        user = factories.AuthUserFactory()
        file_checked = folder_two.append_file('We shall see')
        file_checked.checkout = user
        file_checked.save()

        res = self.delete(folder)
        assert res.status_code == 403


@pytest.mark.django_db
class TestDeleteHookPreprint(TestDeleteHookNode):

    def setUp(self):
        super().setUp()
        self.preprint = PreprintFactory(creator=self.user)
        self.node = self.preprint
        self.root_node = self.preprint.root_folder

    def test_attempt_delete_while_preprint(self):
        res = self.delete(self.preprint.primary_file)
        assert res.status_code == 403

    def test_attempt_delete_folder_with_preprint(self):
        folder = self.root_node.append_folder('Fishes')
        file = folder.append_file('Fish')
        self.preprint.primary_file = file
        self.preprint.save()
        res = self.delete(folder)
        assert res.status_code == 403

    def test_delete_folder_while_preprint(self):
        folder = self.root_node.append_folder('Mr. Yuck')
        preprint_file = self.root_node.append_file('Thyme Out')
        self.preprint.primary_file = preprint_file
        self.preprint.save()
        res = self.delete(folder)
        assert res.status_code == 200

    def test_delete_folder_on_preprint_with_non_preprint_file_inside(self):
        folder = self.root_node.append_folder('Herbal Crooners')
        file = folder.append_file('Frank Cilantro')
        # project having a preprint should not block other moves
        primary_file = self.root_node.append_file('Thyme Out')
        self.preprint.primary_file = primary_file
        self.preprint.save()
        res = self.delete(folder)

        assert res.status_code == 200

@pytest.mark.django_db
class TestMoveHook(HookTestCase):

    def setUp(self):
        super().setUp()
        self.root_node = self.node_settings.get_root()

    def test_move_hook(self):

        file = self.root_node.append_file('Ain\'t_got_no,_I_got_life')
        folder = self.root_node.append_folder('Nina Simone')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.root_node.target._id},
            payload={
                'source': file._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder._id,
                    'target': folder.target._id,
                    'name': folder.name,
                }
            },
            target=self.node,
            method='post',)
        assert res.status_code == 200

    def test_move_checkedout_file(self):

        file = self.root_node.append_file('Ain\'t_got_no,_I_got_life')
        file.checkout = self.user
        file.save()
        folder = self.root_node.append_folder('Nina Simone')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.root_node.target._id},
            payload={
                'source': file._id,  # id of the actual file
                'target': self.root_node._id,  # the source FOLDER
                'user': self.user._id,
                'destination': {
                    'parent': folder._id,  # the destination FOLDER
                    'target': folder.target._id,  # The TARGET for the folder where it is going
                    'name': folder.name,
                }
            },
            target=self.node,
            method='post',
        )
        assert res.status_code == 405

    def test_move_checkedout_file_in_folder(self):
        folder = self.root_node.append_folder('From Here')
        file = folder.append_file('No I don\'t wanna go')
        file.checkout = self.user
        file.save()

        folder_two = self.root_node.append_folder('To There')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.root_node.target._id},
            payload={
                'source': folder._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'target': folder_two.target._id,
                    'name': folder_two.name,
                }
            },
            target=self.node,
            method='post',
        )
        assert res.status_code == 405

    def test_move_checkedout_file_two_deep_in_folder(self):
        folder = self.root_node.append_folder('From Here')
        folder_nested = folder.append_folder('Inbetween')
        file = folder_nested.append_file('No I don\'t wanna go')
        file.checkout = self.user
        file.save()

        folder_two = self.root_node.append_folder('To There')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.root_node.target._id},
            payload={
                'source': folder._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'target': folder_two.target._id,
                    'name': folder_two.name,
                }
            },
            target=self.node,
            method='post',
        )
        assert res.status_code == 405

    def test_move_file_out_of_node(self):
        folder = self.root_node.append_folder('A long time ago')
        file = folder.append_file('in a galaxy')

        project = ProjectFactory(creator=self.user)
        project_settings = project.get_addon('osfstorage')
        project_root_node = project_settings.get_root()

        folder_two = project_root_node.append_folder('far away')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.root_node.target._id},
            payload={
                'source': folder._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'target': folder_two.target._id,
                    'name': folder_two.name,
                }
            },
            target=project,
            method='post',
        )
        assert res.status_code == 200

    def test_can_rename_file(self):
        file = create_test_file(self.node, self.user, filename='road_dogg.mp3')
        new_name = 'JesseJames.mp3'

        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.node._id},
            payload={
                'action': 'rename',
                'source': file._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'name': file.name,
                'destination': {
                    'parent': self.root_node._id,
                    'target': self.node._id,
                    'name': new_name,
                }
            },
            target=self.node,
            method='post',
        )
        file.reload()

        assert res.status_code == 200
        assert file.name == new_name
        assert file.versions.first().get_basefilenode_version(file).version_name == new_name


@pytest.mark.django_db
class TestMoveHookPreprint(TestMoveHook):

    def setUp(self):
        super(TestMoveHook, self).setUp()
        self.node = PreprintFactory(creator=self.user)
        self.root_node = self.node.root_folder

    def test_move_primary_file_out_of_preprint(self):
        project = ProjectFactory(creator=self.user)
        project_settings = project.get_addon('osfstorage')
        project_root_node = project_settings.get_root()

        folder_two = project_root_node.append_folder('To There')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.root_node.target._id},
            payload={
                'source': self.node.primary_file._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'target': folder_two.target._id,
                    'name': folder_two.name,
                }
            },
            target=project,
            method='post',
        )
        assert res.status_code == 403

    def test_can_rename_file(self):
        file = create_test_preprint_file(self.node, self.user, filename='road_dogg.mp3')
        new_name = 'JesseJames.mp3'

        res = self.send_hook(
            'osfstorage_move_hook',
            {'guid': self.node._id},
            payload={
                'action': 'rename',
                'source': file._id,
                'target': self.root_node._id,
                'user': self.user._id,
                'name': file.name,
                'destination': {
                    'parent': self.root_node._id,
                    'target': self.node._id,
                    'name': new_name,
                }
            },
            target=self.node,
            method='post',
        )
        file.reload()

        assert res.status_code == 200
        assert file.name == new_name
        assert file.versions.first().get_basefilenode_version(file).version_name == new_name


@pytest.mark.django_db
class TestMoveHookProjectsOnly(TestMoveHook):

    def test_move_hook_updates_cache_intra_target(self):
        """
        Moving within a single target shouldn't update the cache because net storage usage hasn't changed
        """

        file = create_record_with_version('new file', self.node_settings, size=123)
        folder = self.root_node.append_folder('Nina Simone')

        with override_flag(features.STORAGE_USAGE, active=True):
            res = self.send_hook(
                'osfstorage_move_hook',
                {'guid': self.root_node.target._id},
                payload={
                    'source': file._id,
                    'target': self.root_node._id,
                    'user': self.user._id,
                    'destination': {
                        'parent': folder._id,
                        'target': folder.target._id,
                        'name': folder.name,
                    }
                },
                target=self.node,
                method='post',)

        # Cache should stay untouched because net storage usage hasn't changed
        key = STORAGE_USAGE_KEY.format(target_id=self.project._id)
        assert storage_usage_cache.get(key) is None

        assert res.status_code == 200


@pytest.mark.django_db
class TestFileTags(StorageTestCase):

    def test_file_add_tag(self):
        file = self.node_settings.get_root().append_file('Good Morning.mp3')
        assert 'Kanye_West' not in file.tags.values_list('name', flat=True)

        url = api_url_for('osfstorage_add_tag', guid=self.node._id, fid=file._id)
        self.app.post(url, json={'tag': 'Kanye_West'}, auth=self.user.auth)
        file.reload()
        assert 'Kanye_West' in file.tags.values_list('name', flat=True)

    def test_file_add_non_ascii_tag(self):
        file = self.node_settings.get_root().append_file('JapaneseCharacters.txt')
        assert 'コンサート' not in file.tags.values_list('name', flat=True)

        url = api_url_for('osfstorage_add_tag', guid=self.node._id, fid=file._id)
        self.app.post(url, json={'tag': 'コンサート'}, auth=self.user.auth)
        file.reload()
        assert 'コンサート' in file.tags.values_list('name', flat=True)

    def test_file_remove_tag(self):
        file = self.node_settings.get_root().append_file('Champion.mp3')
        tag = Tag(name='Graduation')
        tag.save()
        file.tags.add(tag)
        file.save()
        assert 'Graduation' in file.tags.values_list('name', flat=True)
        url = api_url_for('osfstorage_remove_tag', guid=self.node._id, fid=file._id)
        self.app.delete(url, json={'tag': 'Graduation'}, auth=self.user.auth)
        file.reload()
        assert 'Graduation' not in file.tags.values_list('name', flat=True)

    def test_tag_the_same_tag(self):
        file = self.node_settings.get_root().append_file('Lie,Cheat,Steal.mp3')
        tag = Tag(name='Run_the_Jewels')
        tag.save()
        file.tags.add(tag)
        file.save()
        assert 'Run_the_Jewels' in file.tags.values_list('name', flat=True)
        url = api_url_for('osfstorage_add_tag', guid=self.node._id, fid=file._id)
        res = self.app.post(url, json={'tag': 'Run_the_Jewels'}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['status'] == 'failure'

    def test_remove_nonexistent_tag(self):
        file = self.node_settings.get_root().append_file('WonderfulEveryday.mp3')
        assert 'Chance' not in file.tags.values_list('name', flat=True)
        url = api_url_for('osfstorage_remove_tag', guid=self.node._id, fid=file._id)
        res = self.app.delete(url, json={'tag': 'Chance'}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['status'] == 'failure'

    def test_file_add_tag_creates_log(self):
        file = self.node_settings.get_root().append_file('Yeezy Season 3.mp4')
        url = api_url_for('osfstorage_add_tag', guid=self.node._id, fid=file._id)
        res = self.app.post(url, json={'tag': 'Kanye_West'}, auth=self.user.auth)

        assert res.status_code == 200
        self.node.reload()
        assert self.node.logs.latest().action == 'file_tag_added'

    @mock.patch('addons.osfstorage.models.OsfStorageFile.add_tag_log')
    def test_file_add_tag_fail_doesnt_create_log(self, mock_log):
        file = self.node_settings.get_root().append_file('UltraLightBeam.mp3')
        tag = Tag(name='The Life of Pablo')
        tag.save()
        file.tags.add(tag)
        file.save()
        url = api_url_for('osfstorage_add_tag', guid=self.node._id, fid=file._id)
        res = self.app.post(url, json={'tag': 'The Life of Pablo'}, auth=self.user.auth)

        assert res.status_code == 400
        mock_log.assert_not_called()

    def test_file_remove_tag_creates_log(self):
        file = self.node_settings.get_root().append_file('Formation.flac')
        tag = Tag(name='You that when you cause all this conversation')
        tag.save()
        file.tags.add(tag)
        file.save()
        url = api_url_for('osfstorage_remove_tag', guid=self.node._id, fid=file._id)
        res = self.app.delete(url, json={'tag': 'You that when you cause all this conversation'}, auth=self.user.auth)

        assert res.status_code == 200
        self.node.reload()
        assert self.node.logs.latest().action == 'file_tag_removed'

    @mock.patch('addons.osfstorage.models.OsfStorageFile.add_tag_log')
    def test_file_remove_tag_fail_doesnt_create_log(self, mock_log):
        file = self.node_settings.get_root().append_file('For-once-in-my-life.mp3')
        url = api_url_for('osfstorage_remove_tag', guid=self.node._id, fid=file._id)
        res = self.app.delete(url, json={'tag': 'wonder'}, auth=self.user.auth)

        assert res.status_code == 400
        mock_log.assert_not_called()


@pytest.mark.django_db
@pytest.mark.enable_bookmark_creation
class TestFileViews(StorageTestCase):

    def add_github(self):
        addon = self.node.add_addon('github', auth=Auth(self.user))
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.add_addon('github')
        self.user.external_accounts.add(oauth_settings)
        self.user.save()
        addon.user_settings = self.user.get_addon('github')
        addon.external_account = oauth_settings
        addon.repo = 'something'
        addon.user = 'someone'
        addon.save()
        addon.user_settings.oauth_grants[self.project._id] = {
            oauth_settings._id: []}
        addon.user_settings.save()
        self.node.save()


    @responses.activate
    def test_file_view_updates_history(self):
        self.add_github()

        # This represents a file add to github via github, without any OSF activity.
        prepare_mock_wb_response(
            folder=False,
            path='/testpath',
            node=self.node,
            provider='github',
            files=[
                {'name': 'testpath', 'path': '/testpath', 'materialized': '/testpath', 'kind': 'file'},
            ]
        )
        with override_flag(features.EMBER_FILE_PROJECT_DETAIL, active=True):
            url = self.node.web_url_for('addon_view_or_download_file', path='testpath', provider='github')
            self.app.get(url, auth=self.user.auth)
            file = GithubFile.objects.get(_path='/testpath', provider='github')
            assert file.history

    @mock.patch('website.views.stream_emberapp')
    def test_file_views(self, mock_ember):
        with override_flag(features.EMBER_FILE_PROJECT_DETAIL, active=True):
            file = create_test_file(target=self.node, user=self.user)
            url = self.node.web_url_for('addon_view_or_download_file', path=file._id, provider=file.provider)
            res = self.app.get(url, auth=self.user.auth)
            assert res.status_code == 302
            assert res.headers['Location'] == f'{settings.DOMAIN}{file.get_guid()._id}/'
            assert not mock_ember.called
            res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
            assert res.status_code == 200
            assert mock_ember.called
            args, kwargs = mock_ember.call_args

            assert args[0] == EXTERNAL_EMBER_APPS['ember_osf_web']['server']
            assert args[1] == EXTERNAL_EMBER_APPS['ember_osf_web']['path'].rstrip('/')

    def test_download_file(self):
        file = create_test_file(target=self.node, user=self.user)
        folder = self.node_settings.get_root().append_folder('Folder')

        base_url = '/download/{}/'

        # Test download works with path
        url = base_url.format(file._id)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 302

        # Test download works with guid
        url = base_url.format(file.get_guid()._id)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 302

        # Test nonexistant file 404's
        url = base_url.format('FakeGuid')
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 404

        # Test folder 400's
        url = base_url.format(folder._id)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 400

    def test_addon_view_file(self):
        file = create_test_file(target=self.node, user=self.user, filename='first_name')
        version = factories.FileVersionFactory()
        file.add_version(version)
        file.move_under(self.node_settings.get_root(), name='second_name')
        file.save()

        version = factories.FileVersionFactory()
        file.add_version(version)
        file.move_under(self.node_settings.get_root(), name='third_name')
        file.save()

        ret = addon_view_file(Auth(self.user), self.node, file, version)
        assert ret['version_names'] == ['third_name', 'second_name', 'first_name']

    def test_osfstorage_download_view(self):
        file = create_test_file(target=self.node, user=self.user)
        version = factories.FileVersionFactory()
        file.add_version(version)
        file.move_under(self.node_settings.get_root(), name='new_name')
        file.save()

        res = self.app.get(
                api_url_for(
                    'osfstorage_download',
                    fid=file._id,
                    guid=self.node._id,
                    **signing.sign_data(signing.default_signer, {})
                ),
                auth=self.user.auth,
            )
        assert res.status_code == 200
        assert res.json['data']['name'] == 'new_name'

    @responses.activate
    @mock.patch('framework.auth.cas.get_client')
    def test_download_file_with_token(self, mock_get_client):
        cas_base_url = 'http://accounts.test.test'
        client = cas.CasClient(cas_base_url)

        mock_get_client.return_value = client

        base_url = '/download/{}/'
        file = create_test_file(target=self.node, user=self.user)

        responses.add(
            responses.Response(
                responses.GET,
                f'{cas_base_url}/oauth2/profile',
                body=json.dumps({'id': f'{self.user._id}'}),
                status=200,
            )
        )

        download_url = base_url.format(file.get_guid()._id)
        token = ApiOAuth2PersonalTokenFactory(owner=self.user)
        headers = {
            'Authorization': f'Bearer {token.token_id}'
        }
        redirect = self.app.get(download_url, headers=headers)

        assert mock_get_client.called
        assert self.node.osfstorage_region.waterbutler_url in redirect.location
        assert redirect.status_code == 302


@pytest.mark.django_db
class TestPreprintFileViews(StorageTestCase):

    def test_file_views(self):
        self.preprint = PreprintFactory(creator=self.user)
        file = self.preprint.primary_file
        guid = file.get_guid(create=True)
        url = self.preprint.web_url_for('resolve_guid', guid=guid._id)
        # File view for preprint file redirects to the preprint
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 302
        assert self.preprint._id in res.location

    def test_download_file(self):
        self.preprint = PreprintFactory(creator=self.user)
        file = self.preprint.primary_file
        folder = self.preprint.root_folder.append_folder('Folder')

        base_url = '/download/{}/'

        # Test download works with path
        url = base_url.format(file._id)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 302

        # Test download works with guid
        url = base_url.format(file.get_guid(create=True)._id)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 302

        # Test nonexistant file 404's
        url = base_url.format('FakeGuid')
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 404

        # Test folder 400's
        url = base_url.format(folder._id)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 400

    @responses.activate
    @mock.patch('framework.auth.cas.get_client')
    def test_download_file_with_token(self, mock_get_client):
        self.preprint = PreprintFactory(creator=self.user)
        file = self.preprint.primary_file

        cas_base_url = 'http://accounts.test.test'
        client = cas.CasClient(cas_base_url)

        mock_get_client.return_value = client

        base_url = '/download/{}/'

        responses.add(
            responses.Response(
                responses.GET,
                f'{cas_base_url}/oauth2/profile',
                body=json.dumps({'id': f'{self.user._id}'}),
                status=200,
            )
        )

        download_url = base_url.format(file.get_guid(create=True)._id)
        token = ApiOAuth2PersonalTokenFactory(owner=self.user)
        headers = {
            'Authorization': f'Bearer {token.token_id}'
        }

        redirect = self.app.get(download_url, headers=headers)

        assert mock_get_client.called
        assert settings.WATERBUTLER_URL in redirect.location
        assert redirect.status_code == 302
