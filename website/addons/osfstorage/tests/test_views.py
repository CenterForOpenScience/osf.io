# encoding: utf-8
from __future__ import unicode_literals

import os
from nose.tools import *  # noqa

from framework.auth.core import Auth
from website.addons.osfstorage.tests.utils import (
    StorageTestCase, Delta, AssertDeltas,
    recursively_create_file,
)
from website.addons.osfstorage.tests import factories

from framework.auth import signing
from website.util import rubeus

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import views
from website.addons.base.views import make_auth
from website.addons.osfstorage import settings as storage_settings


def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    node_settings.root_node.append_file(path)
    record.versions.append(version)
    record.save()
    return record


class HookTestCase(StorageTestCase):

    def send_hook(self, view_name, payload, method='get', **kwargs):
        method = getattr(self.app, method)
        return method(
            self.project.api_url_for(view_name),
            signing.sign_data(signing.default_signer, payload),
            **kwargs
        )


class TestGetMetadataHook(HookTestCase):

    def test_file_metata(self):
        path = u'kind/of/magíc.mp3'
        record = recursively_create_file(self.node_settings, path)
        version = factories.FileVersionFactory()
        record.versions.append(version)
        record.save()
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': record.parent._id},
        )
        assert_equal(len(res.json), 1)
        assert_equal(
            res.json[0],
            record.serialized()
        )

    def test_osf_storage_root(self):
        auth = Auth(self.project.creator)
        result = views.osf_storage_root(self.node_settings, auth=auth)
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
        assert_equal(root, expected)

    def test_root_is_slash(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': '/'},
        )
        assert_equal(res.json, [])

    def test_metadata_not_found(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': '/notfound'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)

    def test_metadata_not_found_lots_of_slashes(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': '/not/fo/u/nd/'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)

    def test_metadata_path_required(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook', {},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)

    def test_metadata_path_empty(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': ''},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)


class TestUploadFileHook(HookTestCase):

    def setUp(self):
        super(TestUploadFileHook, self).setUp()
        self.path = 'pízza.png'
        self.record = recursively_create_file(self.node_settings, self.path)
        self.auth = make_auth(self.user)

    def send_upload_hook(self, payload=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_file_hook',
            payload=payload or {},
            method='post_json',
            **kwargs
        )

    def make_payload(self, **kwargs):
        payload = {
            'auth': self.auth,
            'path': self.path,
            'hashes': {},
            'worker': '',
            'settings': {storage_settings.WATERBUTLER_RESOURCE: 'osf'},
            'metadata': {
                'provider': 'osfstorage',
                'service': 'cloud',
                'name': 'file',
                'size': 123,
                'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
            },
        }
        payload.update(kwargs)
        return payload

    def test_upload_create(self):
        path = 'slightly-mad'
        res = self.send_upload_hook(self.make_payload(path=path))
        self.record.reload()
        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['downloads'], self.record.get_download_count())
        version = model.OsfStorageFileVersion.load(res.json['version'])
        assert_is_not(version, None)
        assert_not_in(version, self.record.versions)
        record = self.node_settings.root_node.find_child_by_name(path)
        assert_in(version, record.versions)

    def test_upload_update(self):
        delta = Delta(lambda: len(self.record.versions), lambda value: value + 1)
        with AssertDeltas(delta):
            res = self.send_upload_hook(self.make_payload())
            self.record.reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        version = model.OsfStorageFileVersion.load(res.json['version'])
        assert_is_not(version, None)
        assert_in(version, self.record.versions)

    def test_upload_duplicate(self):
        location = {
            'service': 'cloud',
            storage_settings.WATERBUTLER_RESOURCE: 'osf',
            'object': 'file',
        }
        version = self.record.create_version(self.user, location)
        with AssertDeltas(Delta(lambda: len(self.record.versions))):
            res = self.send_upload_hook(self.make_payload())
            self.record.reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        version = model.OsfStorageFileVersion.load(res.json['version'])
        assert_is_not(version, None)
        assert_in(version, self.record.versions)

    def test_upload_create_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.root_node.append_folder('cheesey')
        path = os.path.join(parent.path, name)
        res = self.send_upload_hook(self.make_payload(path=path))

        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['downloads'], self.record.get_download_count())

        version = model.OsfStorageFileVersion.load(res.json['version'])

        assert_is_not(version, None)
        assert_not_in(version, self.record.versions)

        record = parent.find_child_by_name(name)
        assert_in(version, record.versions)
        assert_equals(record.name, name)
        assert_equals(record.parent, parent)

    def test_upload_create_child_with_same_name(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        self.node_settings.root_node.append_file(name)
        parent = self.node_settings.root_node.append_folder('cheesey')
        path = os.path.join(parent.path, name)
        res = self.send_upload_hook(self.make_payload(path=path))

        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['downloads'], self.record.get_download_count())

        version = model.OsfStorageFileVersion.load(res.json['version'])

        assert_is_not(version, None)
        assert_not_in(version, self.record.versions)

        record = parent.find_child_by_name(name)
        assert_in(version, record.versions)
        assert_equals(record.name, name)
        assert_equals(record.parent, parent)

    def test_update_nested_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.root_node.append_folder('cheesey')
        old_node = parent.append_file(name)
        path = os.path.join(parent.path, name)

        res = self.send_upload_hook(self.make_payload(path=path))

        old_node.reload()
        new_node = parent.find_child_by_name(name)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['downloads'], new_node.get_download_count())

        assert_equal(old_node, new_node)

        version = model.OsfStorageFileVersion.load(res.json['version'])

        assert_is_not(version, None)
        assert_in(version, new_node.versions)

        assert_in(version, new_node.versions)
        assert_equals(new_node.name, name)
        assert_equals(new_node.parent, parent)

    def test_upload_weired_name(self):
        name = 'another/dir/carpe.png'
        parent = self.node_settings.root_node.append_folder('cheesey')
        path = os.path.join(parent.path, name)
        res = self.send_upload_hook(self.make_payload(path=path), expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(len(parent.children), 0)

    def test_upload_no_data(self):
        res = self.send_upload_hook(expect_errors=True)

        assert_equal(res.status_code, 400)

    # def test_upload_update_deleted(self):
    #     pass


class TestUpdateMetadataHook(HookTestCase):

    def setUp(self):
        super(TestUpdateMetadataHook, self).setUp()
        self.path = 'greasy/pízza.png'
        self.record = recursively_create_file(self.node_settings, self.path)
        self.version = factories.FileVersionFactory()
        self.record.versions = [self.version]
        self.record.save()
        self.payload = {
            'metadata': {'archive': 'glacier', 'size': 123, 'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'},
            'version': self.version._id,
            'size': 123,
        }

    def send_metadata_hook(self, payload=None, **kwargs):
        return self.send_hook(
            'osf_storage_update_metadata_hook',
            payload=payload or self.payload,
            method='put_json',
            **kwargs
        )

    def test_archived(self):
        self.send_metadata_hook()
        self.version.reload()
        assert_in('archive', self.version.metadata)
        assert_equal(self.version.metadata['archive'], 'glacier')

    def test_archived_record_not_found(self):
        res = self.send_metadata_hook(
            payload={
                'metadata': {'archive': 'glacier'},
                'version': self.version._id[::-1],
                'size': 123,
                'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        self.version.reload()
        assert_not_in('archive', self.version.metadata)


class TestGetRevisions(StorageTestCase):

    def setUp(self):
        super(TestGetRevisions, self).setUp()
        self.path = 'tie/your/mother/down.mp3'
        self.record = recursively_create_file(self.node_settings, self.path)
        self.record.versions = [factories.FileVersionFactory() for __ in range(15)]
        self.record.save()

    def get_revisions(self, path=None, **kwargs):
        return self.app.get(
            self.project.api_url_for(
                'osf_storage_get_revisions',
                **signing.sign_data(
                    signing.default_signer,
                    {
                        'path': path or self.record.path,
                    }
                )
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
                index=len(self.record.versions) - 1 - idx
            )
            for idx, version in enumerate(reversed(self.record.versions))
        ]

        assert_equal(len(res.json['revisions']), 15)
        assert_equal(res.json['revisions'], [x for x in expected])
        assert_equal(res.json['revisions'][0]['index'], 15)
        assert_equal(res.json['revisions'][-1]['index'], 1)

    def test_get_revisions_no_path(self):
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_get_revisions',
                **signing.sign_data(
                    signing.default_signer,
                    {}
                )
            ),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_get_revisions_path_not_found(self):
        res = self.get_revisions(path='missing', expect_errors=True)
        assert_equal(res.status_code, 404)


class TestCreateFolder(HookTestCase):

    def setUp(self):
        super(TestCreateFolder, self).setUp()
        self.root_node = self.node_settings.root_node

    def create_folder(self, name, parent=None, **kwargs):
        parent = parent + '/' if parent else ''
        return self.send_hook(
            'osf_storage_create_folder',
            payload={
                'path': '/{}{}'.format(parent, name),
                'cookie': self.user.get_or_create_cookie()
            },
            method='post_json',
            **kwargs
        )

    def test_create_folder(self):
        resp = self.create_folder('name')

        assert_equal(resp.status_code, 201)
        assert_equal(len(self.root_node.children), 1)
        assert_equal(self.root_node.children[0].serialized(), resp.json)

    def test_no_data(self):
        resp = self.send_hook(
            'osf_storage_create_folder',
            payload={},
            method='post_json',
            expect_errors=True
        )
        assert_equal(resp.status_code, 400)

    def test_create_with_parent(self):
        resp = self.create_folder('name')

        assert_equal(resp.status_code, 201)
        assert_equal(len(self.root_node.children), 1)
        assert_equal(self.root_node.children[0].serialized(), resp.json)

        resp = self.create_folder('name', parent=resp.json['path'].strip('/'))

        assert_equal(resp.status_code, 201)
        assert_equal(len(self.root_node.children), 1)
        assert_equal(len(self.root_node.children[0].children), 1)
        assert_equal(self.root_node.children[0].children[0].serialized(), resp.json)


class TestDeleteHook(HookTestCase):

    def setUp(self):
        super(TestDeleteHook, self).setUp()
        self.root_node = self.node_settings.root_node

    def send_hook(self, view_name, payload, method='get', **kwargs):
        method = getattr(self.app, method)
        return method(
            '{url}?payload={payload}&signature={signature}'.format(
                url=self.project.api_url_for(view_name),
                **signing.sign_data(signing.default_signer, payload)
            ),
            **kwargs
        )

    def delete(self, path, **kwargs):
        return self.send_hook(
            'osf_storage_crud_hook_delete',
            payload={
                'path': path,
                'auth': {
                    'id': self.user._id
                }
            },
            method='delete',
            **kwargs
        )

    def test_delete(self):
        file = self.root_node.append_file('Newfile')

        resp = self.delete(file.path)

        file.reload()
        assert_true(file.is_deleted)
        assert_equal(resp.status_code, 200)
        assert_equal(resp.json, {'status': 'success'})

    def test_delete_deleted(self):
        file = self.root_node.append_file('Newfile')
        file.delete(None, log=False)
        assert_true(file.is_deleted)

        resp = self.delete(file.path, expect_errors=True)

        file.reload()
        assert_equal(resp.status_code, 410)

    def test_cannot_delete_root(self):
        resp = self.delete(self.root_node.path, expect_errors=True)

        assert_equal(resp.status_code, 400)
