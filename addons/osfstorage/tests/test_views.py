# encoding: utf-8
from __future__ import unicode_literals

import mock
import datetime

import pytest
from nose.tools import *  # noqa
from dateutil.parser import parse as parse_datetime

from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from framework.auth.core import Auth
from addons.osfstorage.tests.utils import (
    StorageTestCase, Delta, AssertDeltas,
    recursively_create_file,
)
from addons.osfstorage.tests import factories
from addons.osfstorage.tests.utils import make_payload

from framework.auth import signing
from website.util import rubeus

from osf.models import Tag, QuickFilesNode
from osf.models import files as models
from addons.osfstorage.apps import osf_storage_root
from addons.osfstorage import utils
from addons.base.views import make_auth
from addons.osfstorage import settings as storage_settings
from api_tests.utils import create_test_file

from osf_tests.factories import ProjectFactory

def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    node_settings.get_root().append_file(path)
    record.versions.append(version)
    record.save()
    return record


@pytest.mark.django_db
class HookTestCase(StorageTestCase):

    def send_hook(self, view_name, view_kwargs, payload, method='get', **kwargs):
        method = getattr(self.app, method)
        return method(
            self.project.api_url_for(view_name, **view_kwargs),
            signing.sign_data(signing.default_signer, payload),
            **kwargs
        )


@pytest.mark.django_db
class TestGetMetadataHook(HookTestCase):

    def test_empty(self):
        res = self.send_hook(
            'osfstorage_get_children',
            {'fid': self.node_settings.get_root()._id},
            {},
        )
        assert_true(isinstance(res.json, list))
        assert_equal(res.json, [])

    def test_file_metdata(self):
        path = u'kind/of/magíc.mp3'
        record = recursively_create_file(self.node_settings, path)
        version = factories.FileVersionFactory()
        record.versions.add(version)
        record.save()
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': record.parent._id},
            {},
        )
        assert_true(isinstance(res.json, dict))
        assert_equal(res.json, record.parent.serialize(True))

    def test_children_metadata(self):
        path = u'kind/of/magíc.mp3'
        record = recursively_create_file(self.node_settings, path)
        version = factories.FileVersionFactory()
        record.versions.add(version)
        record.save()
        res = self.send_hook(
            'osfstorage_get_children',
            {'fid': record.parent._id},
            {},
        )
        assert_equal(len(res.json), 1)
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

        assert_equal(res_date_modified, expected_date_modified)
        assert_equal(res_date_created, expected_date_created)
        assert_equal(res_data, expected_data)

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
        assert_equal(root, expected)

    def test_root_default(self):
        res = self.send_hook('osfstorage_get_metadata', {}, {})

        assert_equal(res.json['fullPath'], '/')
        assert_equal(res.json['id'], self.node_settings.get_root()._id)

    def test_metadata_not_found(self):
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': 'somebogusid'}, {},
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)

    def test_metadata_not_found_lots_of_slashes(self):
        res = self.send_hook(
            'osfstorage_get_metadata',
            {'fid': '/not/fo/u/nd/'}, {},
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)


@pytest.mark.django_db
class TestUploadFileHook(HookTestCase):

    def setUp(self):
        super(TestUploadFileHook, self).setUp()
        self.name = 'pízza.png'
        self.record = recursively_create_file(self.node_settings, self.name)
        self.auth = make_auth(self.user)

    def send_upload_hook(self, parent, payload=None, **kwargs):
        return self.send_hook(
            'osfstorage_create_child',
            {'fid': parent._id},
            payload=payload or {},
            method='post_json',
            **kwargs
        )

    def make_payload(self, **kwargs):
        user = kwargs.pop('user', self.user)
        name = kwargs.pop('name', self.name)
        return make_payload(user=user, name=name, **kwargs)

    def test_upload_create(self):
        name = 'slightly-mad'

        res = self.send_upload_hook(self.node_settings.get_root(), self.make_payload(name=name))

        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')

        record = self.node_settings.get_root().find_child_by_name(name)
        version = models.FileVersion.load(res.json['version'])

        assert_equal(version.size, 123)
        assert_equal(version.location_hash, 'file')

        assert_equal(version.location, {
            'object': 'file',
            'uname': 'testmachine',
            'service': 'filesystem',
            'provider': 'filesystem',
            storage_settings.WATERBUTLER_RESOURCE: 'blah',
        })
        assert_equal(version.metadata, {
            'size': 123,
            'name': 'file',
            'base64': '==',
            'provider': 'filesystem',
            'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
        })

        assert_is_not(version, None)
        assert_equal([version], list(record.versions.all()))
        assert_not_in(version, self.record.versions.all())
        assert_equal(record.serialize(), res.json['data'])
        assert_equal(res.json['data']['downloads'], self.record.get_download_count())

    def test_upload_update(self):
        delta = Delta(lambda: self.record.versions.count(), lambda value: value + 1)
        with AssertDeltas(delta):
            res = self.send_upload_hook(self.node_settings.get_root(), self.make_payload())
            self.record.reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        version = models.FileVersion.load(res.json['version'])
        assert_is_not(version, None)
        assert_in(version, self.record.versions.all())

    def test_upload_duplicate(self):
        location = {
            'service': 'cloud',
            storage_settings.WATERBUTLER_RESOURCE: 'osf',
            'object': 'file',
        }
        version = self.record.create_version(self.user, location)
        with AssertDeltas(Delta(lambda: self.record.versions.count())):
            res = self.send_upload_hook(self.node_settings.get_root(), self.make_payload())
            self.record.reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        version = models.FileVersion.load(res.json['version'])
        assert_is_not(version, None)
        assert_in(version, self.record.versions.all())

    def test_upload_create_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, self.make_payload(name=name))

        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['data']['downloads'], self.record.get_download_count())

        version = models.FileVersion.load(res.json['version'])

        assert_is_not(version, None)
        assert_not_in(version, self.record.versions.all())

        record = parent.find_child_by_name(name)
        assert_in(version, record.versions.all())
        assert_equals(record.name, name)
        assert_equals(record.parent, parent)

    def test_upload_create_child_with_same_name(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        self.node_settings.get_root().append_file(name)
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, self.make_payload(name=name))

        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['data']['downloads'], self.record.get_download_count())

        version = models.FileVersion.load(res.json['version'])

        assert_is_not(version, None)
        assert_not_in(version, self.record.versions.all())

        record = parent.find_child_by_name(name)
        assert_in(version, record.versions.all())
        assert_equals(record.name, name)
        assert_equals(record.parent, parent)

    def test_upload_fail_to_create_version_due_to_checkout(self):
        user = factories.AuthUserFactory()
        name = 'Gunter\'s noise.mp3'
        self.node_settings.get_root().append_file(name)
        root = self.node_settings.get_root()
        file = root.find_child_by_name(name)
        file.checkout = user
        file.save()
        res = self.send_upload_hook(root, self.make_payload(name=name), expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_update_nested_child(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.get_root().append_folder('cheesey')
        old_node = parent.append_file(name)

        res = self.send_upload_hook(parent, self.make_payload(name=name))

        old_node.reload()
        new_node = parent.find_child_by_name(name)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        assert_equal(res.json['data']['downloads'], new_node.get_download_count())

        assert_equal(old_node, new_node)

        version = models.FileVersion.load(res.json['version'])

        assert_is_not(version, None)
        assert_in(version, new_node.versions.all())

        assert_in(version, new_node.versions.all())
        assert_equals(new_node.name, name)
        assert_equals(new_node.parent, parent)

    def test_upload_weird_name(self):
        name = 'another/dir/carpe.png'
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, self.make_payload(name=name), expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(len(parent.children), 0)

    def test_upload_to_file(self):
        name = 'carpe.png'
        parent = self.node_settings.get_root().append_file('cheesey')
        res = self.send_upload_hook(parent, self.make_payload(name=name), expect_errors=True)

        assert_true(parent.is_file)
        assert_equal(res.status_code, 400)

    def test_upload_no_data(self):
        res = self.send_upload_hook(self.node_settings.get_root(), expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_archive(self):
        name = 'ლ(ಠ益ಠლ).unicode'
        parent = self.node_settings.get_root().append_folder('cheesey')
        res = self.send_upload_hook(parent, self.make_payload(name=name, hashes={'sha256': 'foo'}))

        assert_equal(res.status_code, 201)
        assert_equal(res.json['status'], 'success')
        assert_is(res.json['archive'], True)

        res = self.send_hook(
            'osfstorage_update_metadata',
            {},
            payload={'metadata': {
                'vault': 'Vault 101',
                'archive': '101 tluaV',
            }, 'version': res.json['version']},
            method='put_json',
        )

        res = self.send_upload_hook(parent, self.make_payload(
            name=name,
            hashes={'sha256': 'foo'},
            metadata={
                'name': 'lakdjf',
                'provider': 'testing',
            }))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        assert_is(res.json['archive'], False)

    # def test_upload_update_deleted(self):
    #     pass


@pytest.mark.django_db
class TestUpdateMetadataHook(HookTestCase):

    def setUp(self):
        super(TestUpdateMetadataHook, self).setUp()
        self.path = 'greasy/pízza.png'
        self.record = recursively_create_file(self.node_settings, self.path)
        self.version = factories.FileVersionFactory()
        self.record.versions = [self.version]
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

    def send_metadata_hook(self, payload=None, **kwargs):
        return self.send_hook(
            'osfstorage_update_metadata',
            {},
            payload=payload or self.payload,
            method='put_json',
            **kwargs
        )

    def test_callback(self):
        self.version.external_modified = None
        self.version.save()
        self.send_metadata_hook()
        self.version.reload()
        #Test fields are added
        assert_equal(self.version.metadata['size'], 123)
        assert_equal(self.version.metadata['md5'], 'askjasdlk;jsadlkjsadf')
        assert_equal(self.version.metadata['modified'], 'Mon, 16 Feb 2015 18:45:34 GMT')

        #Test attributes are populated
        assert_equal(self.version.size, 123)
        assert_true(isinstance(self.version.external_modified, datetime.datetime))

    def test_archived(self):
        self.send_metadata_hook({
            'version': self.version._id,
            'metadata': {
                'vault': 'osf_storage_prod',
                'archive': 'Some really long glacier object id here'
            }
        })
        self.version.reload()

        assert_equal(self.version.metadata['vault'], 'osf_storage_prod')
        assert_equal(self.version.metadata['archive'], 'Some really long glacier object id here')

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


@pytest.mark.django_db
class TestGetRevisions(StorageTestCase):

    def setUp(self):
        super(TestGetRevisions, self).setUp()
        self.path = 'tie/your/mother/down.mp3'
        self.record = recursively_create_file(self.node_settings, self.path)
        self.record.versions = [factories.FileVersionFactory() for __ in range(15)]
        self.record.save()

    def get_revisions(self, fid=None, **kwargs):
        return self.app.get(
            self.project.api_url_for(
                'osfstorage_get_revisions',
                fid=fid or self.record._id,
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

        assert_equal(len(res.json['revisions']), 15)
        assert_equal(res.json['revisions'], [x for x in expected])
        assert_equal(res.json['revisions'][0]['index'], 15)
        assert_equal(res.json['revisions'][-1]['index'], 1)

    def test_get_revisions_path_not_found(self):
        res = self.get_revisions(fid='missing', expect_errors=True)
        assert_equal(res.status_code, 404)


@pytest.mark.django_db
class TestCreateFolder(HookTestCase):

    def setUp(self):
        super(TestCreateFolder, self).setUp()
        self.root_node = self.node_settings.get_root()

    def create_folder(self, name, parent=None, **kwargs):
        parent = parent or self.node_settings.get_root()

        return self.send_hook(
            'osfstorage_create_child',
            {'fid': parent._id},
            payload={
                'name': name,
                'user': self.user._id,
                'kind': 'folder'
            },
            method='post_json',
            **kwargs
        )

    def test_create_folder(self):
        resp = self.create_folder('name')

        self.root_node.reload()

        assert_equal(resp.status_code, 201)
        assert_equal(len(self.root_node.children), 1)
        assert_equal(self.root_node.children[0].serialize(), resp.json['data'])

    def test_no_data(self):
        resp = self.send_hook(
            'osfstorage_create_child',
            {'fid': self.root_node._id},
            payload={},
            method='post_json',
            expect_errors=True
        )
        assert_equal(resp.status_code, 400)

    def test_create_with_parent(self):
        resp = self.create_folder('name')

        assert_equal(resp.status_code, 201)
        assert_equal(self.root_node.children.count(), 1)
        assert_equal(self.root_node.children.all()[0].serialize(), resp.json['data'])

        resp = self.create_folder('name', parent=OsfStorageFileNode.load(resp.json['data']['id']))

        assert_equal(resp.status_code, 201)
        assert_equal(self.root_node.children.count(), 1)
        assert_false(self.root_node.children.all()[0].is_file)
        assert_equal(self.root_node.children.all()[0].children.count(), 1)
        assert_false(self.root_node.children.all()[0].children.all()[0].is_file)
        assert_equal(self.root_node.children.all()[0].children.all()[0].serialize(), resp.json['data'])


@pytest.mark.django_db
class TestDeleteHook(HookTestCase):

    def setUp(self):
        super(TestDeleteHook, self).setUp()
        self.root_node = self.node_settings.get_root()

    def send_hook(self, view_name, view_kwargs, payload, method='get', **kwargs):
        method = getattr(self.app, method)
        return method(
            '{url}?payload={payload}&signature={signature}'.format(
                url=self.project.api_url_for(view_name, **view_kwargs),
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
            method='delete',
            **kwargs
        )

    def test_delete(self):
        file = self.root_node.append_file('Newfile')

        resp = self.delete(file)

        assert_equal(resp.status_code, 200)
        assert_equal(resp.json, {'status': 'success'})
        fid = file._id
        del file
        # models.StoredFileNode._clear_object_cache()
        assert_is(OsfStorageFileNode.load(fid), None)
        assert_true(models.TrashedFileNode.load(fid))

    def test_delete_deleted(self):
        file = self.root_node.append_file('Newfile')
        file.delete()

        resp = self.delete(file, expect_errors=True)

        assert_equal(resp.status_code, 404)

    def test_cannot_delete_root(self):
        resp = self.delete(self.root_node, expect_errors=True)

        assert_equal(resp.status_code, 400)

    def test_attempt_delete_rented_file(self):
        user = factories.AuthUserFactory()
        file_checked = self.root_node.append_file('Newfile')
        file_checked.checkout = user
        file_checked.save()

        res = self.delete(file_checked, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_attempt_delete_while_preprint(self):
        file = self.root_node.append_file('Nights')
        self.node.preprint_file = file
        self.node.save()
        res = self.delete(file, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_attempt_delete_folder_with_preprint(self):
        folder = self.root_node.append_folder('Fishes')
        file = folder.append_file('Fish')
        self.node.preprint_file = file
        self.node.save()
        res = self.delete(folder, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_delete_folder_while_preprint(self):
        folder = self.root_node.append_folder('Mr. Yuck')
        preprint_file = self.root_node.append_file('Thyme Out')
        self.node.preprint_file = preprint_file
        self.node.save()
        res = self.delete(folder)

        assert_equal(res.status_code, 200)

    def test_delete_folder_on_preprint_with_non_preprint_file_inside(self):
        folder = self.root_node.append_folder('Herbal Crooners')
        file = folder.append_file('Frank Cilantro')
        # project having a preprint should not block other moves
        preprint_file = self.root_node.append_file('Thyme Out')
        self.node.preprint_file = preprint_file
        self.node.save()
        res = self.delete(folder)

        assert_equal(res.status_code, 200)

    def test_attempt_delete_folder_with_rented_file(self):
        folder = self.root_node.append_folder('Hotel Events')
        user = factories.AuthUserFactory()
        file_checked = folder.append_file('Checkout time')
        file_checked.checkout = user
        file_checked.save()

        res = self.delete(folder, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_attempt_delete_double_nested_folder_rented_file(self):
        folder = self.root_node.append_folder('One is not enough')
        folder_two = folder.append_folder('Two might be doe')
        user = factories.AuthUserFactory()
        file_checked = folder_two.append_file('We shall see')
        file_checked.checkout = user
        file_checked.save()

        res = self.delete(folder, expect_errors=True)
        assert_equal(res.status_code, 403)


@pytest.mark.django_db
class TestMoveHook(HookTestCase):

    def setUp(self):
        super(TestMoveHook, self).setUp()
        self.root_node = self.node_settings.get_root()

    def test_move_hook(self):

        file = self.root_node.append_file('Ain\'t_got_no,_I_got_life')
        folder = self.root_node.append_folder('Nina Simone')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': file._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder._id,
                    'node': folder.node._id,
                    'name': folder.name,
                }
            },
            method='post_json',)
        assert_equal(res.status_code, 200)

    def test_move_checkedout_file(self):

        file = self.root_node.append_file('Ain\'t_got_no,_I_got_life')
        file.checkout = self.user
        file.save()
        folder = self.root_node.append_folder('Nina Simone')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': file._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder._id,
                    'node': folder.node._id,
                    'name': folder.name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        assert_equal(res.status_code, 405)

    def test_move_checkedout_file_in_folder(self):
        folder = self.root_node.append_folder('From Here')
        file = folder.append_file('No I don\'t wanna go')
        file.checkout = self.user
        file.save()
        
        folder_two = self.root_node.append_folder('To There')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': folder._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'node': folder_two.node._id,
                    'name': folder_two.name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        assert_equal(res.status_code, 405)

    def test_move_checkedout_file_two_deep_in_folder(self):
        folder = self.root_node.append_folder('From Here')
        folder_nested = folder.append_folder('Inbetween')
        file = folder_nested.append_file('No I don\'t wanna go')
        file.checkout = self.user
        file.save()
        
        folder_two = self.root_node.append_folder('To There')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': folder._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'node': folder_two.node._id,
                    'name': folder_two.name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        assert_equal(res.status_code, 405)


    def test_move_preprint_file_out_of_node(self):
        folder = self.root_node.append_folder('From Here')
        file = folder.append_file('No I don\'t wanna go')
        self.node.preprint_file = file
        self.node.save()

        project = ProjectFactory(creator=self.user)
        project_settings = project.get_addon('osfstorage')
        project_root_node = project_settings.get_root()

        folder_two = project_root_node.append_folder('To There')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': folder._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'node': folder_two.node._id,
                    'name': folder_two.name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        assert_equal(res.status_code, 403)


    def test_move_file_out_of_node(self):
        folder = self.root_node.append_folder('A long time ago')
        file = folder.append_file('in a galaxy')
        # project having a preprint should not block other moves
        preprint_file = self.root_node.append_file('far')
        self.node.preprint_file = preprint_file
        self.node.save()

        project = ProjectFactory(creator=self.user)
        project_settings = project.get_addon('osfstorage')
        project_root_node = project_settings.get_root()

        folder_two = project_root_node.append_folder('far away')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': folder._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder_two._id,
                    'node': folder_two.node._id,
                    'name': folder_two.name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        assert_equal(res.status_code, 200)


    def test_within_node_move_while_preprint(self):

        file = self.root_node.append_file('Self Control')
        self.node.preprint_file = file
        self.node.save()
        folder = self.root_node.append_folder('Frank Ocean')
        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': self.root_node.node._id},
            payload={
                'source': file._id,
                'node': self.root_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': folder._id,
                    'node': folder.node._id,
                    'name': folder.name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        assert_equal(res.status_code, 200)

    def test_can_move_file_out_of_quickfiles_node(self):
        quickfiles_node = QuickFilesNode.objects.get_for_user(self.user)
        create_test_file(quickfiles_node, self.user, filename='slippery.mp3')
        quickfiles_folder = OsfStorageFolder.objects.get(node=quickfiles_node)
        dest_folder = OsfStorageFolder.objects.get(node=self.project)

        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': quickfiles_node._id},
            payload={
                'source': quickfiles_folder._id,
                'node': quickfiles_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': dest_folder._id,
                    'node': self.project._id,
                    'name': dest_folder.name,
                }
            },
            method='post_json',
        )
        assert_equal(res.status_code, 200)

    def test_can_rename_file_in_quickfiles_node(self):
        quickfiles_node = QuickFilesNode.objects.get_for_user(self.user)
        quickfiles_file = create_test_file(quickfiles_node, self.user, filename='road_dogg.mp3')
        quickfiles_folder = OsfStorageFolder.objects.get(node=quickfiles_node)
        dest_folder = OsfStorageFolder.objects.get(node=self.project)
        new_name = 'JesseJames.mp3'

        res = self.send_hook(
            'osfstorage_move_hook',
            {'nid': quickfiles_node._id},
            payload={
                'action': 'rename',
                'source': quickfiles_file._id,
                'node': quickfiles_node._id,
                'user': self.user._id,
                'name': quickfiles_file.name,
                'destination': {
                    'parent': quickfiles_folder._id,
                    'node': quickfiles_node._id,
                    'name': new_name,
                }
            },
            method='post_json',
            expect_errors=True,
        )
        quickfiles_file.reload()

        assert_equal(res.status_code, 200)
        assert_equal(quickfiles_file.name, new_name)


@pytest.mark.django_db
class TestCopyHook(HookTestCase):
    def test_can_copy_file_out_of_quickfiles_node(self):
        quickfiles_node = QuickFilesNode.objects.get_for_user(self.user)
        create_test_file(quickfiles_node, self.user, filename='dont_copy_meeeeeeeee.mp3')
        quickfiles_folder = OsfStorageFolder.objects.get(node=quickfiles_node)
        dest_folder = OsfStorageFolder.objects.get(node=self.project)

        res = self.send_hook(
            'osfstorage_copy_hook',
            {'nid': quickfiles_node._id},
            payload={
                'source': quickfiles_folder._id,
                'node': quickfiles_node._id,
                'user': self.user._id,
                'destination': {
                    'parent': dest_folder._id,
                    'node': self.project._id,
                    'name': dest_folder.name,
                }
            },
            method='post_json',
        )
        assert_equal(res.status_code, 201)


@pytest.mark.django_db
class TestFileTags(StorageTestCase):

    def test_file_add_tag(self):
        file = self.node_settings.get_root().append_file('Good Morning.mp3')
        assert_not_in('Kanye_West', file.tags.values_list('name', flat=True))

        url = self.project.api_url_for('osfstorage_add_tag', fid=file._id)
        self.app.post_json(url, {'tag': 'Kanye_West'}, auth=self.user.auth)
        file.reload()
        assert_in('Kanye_West', file.tags.values_list('name', flat=True))

    def test_file_add_non_ascii_tag(self):
        file = self.node_settings.get_root().append_file('JapaneseCharacters.txt')
        assert_not_in('コンサート', file.tags.values_list('name', flat=True))

        url = self.project.api_url_for('osfstorage_add_tag', fid=file._id)
        self.app.post_json(url, {'tag': 'コンサート'}, auth=self.user.auth)
        file.reload()
        assert_in('コンサート', file.tags.values_list('name', flat=True))

    def test_file_remove_tag(self):
        file = self.node_settings.get_root().append_file('Champion.mp3')
        tag = Tag(name='Graduation')
        tag.save()
        file.tags.add(tag)
        file.save()
        assert_in('Graduation', file.tags.values_list('name', flat=True))
        url = self.project.api_url_for('osfstorage_remove_tag', fid=file._id)
        self.app.delete_json(url, {'tag': 'Graduation'}, auth=self.user.auth)
        file.reload()
        assert_not_in('Graduation', file.tags.values_list('name', flat=True))

    def test_tag_the_same_tag(self):
        file = self.node_settings.get_root().append_file('Lie,Cheat,Steal.mp3')
        tag = Tag(name='Run_the_Jewels')
        tag.save()
        file.tags.add(tag)
        file.save()
        assert_in('Run_the_Jewels', file.tags.values_list('name', flat=True))
        url = self.project.api_url_for('osfstorage_add_tag', fid=file._id)
        res = self.app.post_json(url, {'tag': 'Run_the_Jewels'}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['status'], 'failure')

    def test_remove_nonexistent_tag(self):
        file = self.node_settings.get_root().append_file('WonderfulEveryday.mp3')
        assert_not_in('Chance', file.tags.values_list('name', flat=True))
        url = self.project.api_url_for('osfstorage_remove_tag', fid=file._id)
        res = self.app.delete_json(url, {'tag': 'Chance'}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['status'], 'failure')

    def test_file_add_tag_creates_log(self):
        file = self.node_settings.get_root().append_file('Yeezy Season 3.mp4')
        url = self.project.api_url_for('osfstorage_add_tag', fid=file._id)
        res = self.app.post_json(url, {'tag': 'Kanye_West'}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_equal(self.node.logs.latest().action, 'file_tag_added')

    @mock.patch('addons.osfstorage.models.OsfStorageFile.add_tag_log')
    def test_file_add_tag_fail_doesnt_create_log(self, mock_log):
        file = self.node_settings.get_root().append_file('UltraLightBeam.mp3')
        tag = Tag(name='The Life of Pablo')
        tag.save()
        file.tags.add(tag)
        file.save()
        url = self.project.api_url_for('osfstorage_add_tag', fid=file._id)
        res = self.app.post_json(url, {'tag': 'The Life of Pablo'}, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        mock_log.assert_not_called()

    def test_file_remove_tag_creates_log(self):
        file = self.node_settings.get_root().append_file('Formation.flac')
        tag = Tag(name='You that when you cause all this conversation')
        tag.save()
        file.tags.add(tag)
        file.save()
        url = self.project.api_url_for('osfstorage_remove_tag', fid=file._id)
        res = self.app.delete_json(url, {'tag': 'You that when you cause all this conversation'}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_equal(self.node.logs.latest().action, 'file_tag_removed')

    @mock.patch('addons.osfstorage.models.OsfStorageFile.add_tag_log')
    def test_file_remove_tag_fail_doesnt_create_log(self, mock_log):
        file = self.node_settings.get_root().append_file('For-once-in-my-life.mp3')
        url = self.project.api_url_for('osfstorage_remove_tag', fid=file._id)
        res = self.app.delete_json(url, {'tag': 'wonder'}, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        mock_log.assert_not_called()


@pytest.mark.django_db
class TestFileViews(StorageTestCase):

    def test_file_views(self):
        file = create_test_file(node=self.node, user=self.user)
        url = self.node.web_url_for('addon_view_or_download_file', path=file._id, provider=file.provider)
        # Test valid url file 200 on redirect
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 302
        res = redirect.follow(auth=self.user.auth)
        assert res.status_code == 200

        # Test invalid node but valid deep_url redirects (moved log urls)
        project_two = ProjectFactory(creator=self.user)
        url = project_two.web_url_for('addon_view_or_download_file', path=file._id, provider=file.provider)
        redirect = self.app.get(url, auth=self.user.auth)
        assert redirect.status_code == 302
        redirect_two = redirect.follow(auth=self.user.auth)
        assert redirect_two.status_code == 302
        res = redirect_two.follow(auth=self.user.auth)
        assert res.status_code == 200

    def test_download_file(self):
        file = create_test_file(node=self.node, user=self.user)
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
        redirect = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert redirect.status_code == 404

        # Test folder 400's
        url = base_url.format(folder._id)
        redirect = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert redirect.status_code == 400
