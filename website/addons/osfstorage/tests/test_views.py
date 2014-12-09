#!/usr/bin/env python
# encoding: utf-8

import mock
from nose.tools import *  # noqa

import datetime

from website.addons.osfstorage.tests.utils import (
    StorageTestCase, Delta, AssertDeltas
)
from website.addons.osfstorage.tests import factories

import urlparse

import furl
import markupsafe

from website import settings

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import views
from website.addons.osfstorage import settings as storage_settings


def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    record = model.OsfStorageFileRecord.get_or_create(path, node_settings)
    record.versions.append(version)
    record.save()
    return record


class TestHGridViews(StorageTestCase):

    def test_hgrid_contents(self):
        path = u'kind/of/magíc.mp3'
        model.OsfStorageFileRecord.get_or_create(
            path=path,
            node_settings=self.node_settings,
        )
        version = factories.FileVersionFactory()
        record = model.OsfStorageFileRecord.find_by_path(path, self.node_settings)
        record.versions.append(version)
        record.save()
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_hgrid_contents',
                path='kind/of',
            ),
            auth=self.project.creator.auth,
        )
        assert_equal(len(res.json), 1)
        assert_equal(
            res.json[0],
            utils.serialize_metadata_hgrid(
                record,
                self.project,
                {
                    'edit': True,
                    'view': True,
                }
            )
        )

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_hgrid_contents_pending_one_version_not_expired(self, mock_time):
        mock_time.return_value = 0
        record = model.OsfStorageFileRecord.get_or_create('rhapsody', self.node_settings)
        record.create_pending_version(self.user, '16a383')
        res = self.app.get(
            self.project.api_url_for('osf_storage_hgrid_contents'),
            auth=self.project.creator.auth,
        )
        assert_equal(len(res.json), 1)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_hgrid_contents_pending_one_version_expired(self, mock_time):
        mock_time.return_value = 0
        record = model.OsfStorageFileRecord.get_or_create('rhapsody', self.node_settings)
        record.create_pending_version(self.user, '16a383')
        mock_time.return_value = storage_settings.PING_TIMEOUT + 1
        res = self.app.get(
            self.project.api_url_for('osf_storage_hgrid_contents'),
            auth=self.project.creator.auth,
        )
        assert_equal(len(res.json), 0)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_hgrid_contents_pending_many_versions_not_expired(self, mock_time):
        mock_time.return_value = 0
        record = model.OsfStorageFileRecord.get_or_create('rhapsody', self.node_settings)
        record.versions = [factories.FileVersionFactory() for _ in range(5)]
        record.save()
        record.create_pending_version(self.user, '16a383')
        res = self.app.get(
            self.project.api_url_for('osf_storage_hgrid_contents'),
            auth=self.project.creator.auth,
        )
        assert_equal(len(res.json), 1)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_hgrid_contents_pending_many_versions_expired(self, mock_time):
        mock_time.return_value = 0
        record = model.OsfStorageFileRecord.get_or_create('rhapsody', self.node_settings)
        record.versions = [factories.FileVersionFactory() for _ in range(5)]
        record.save()
        record.create_pending_version(self.user, '16a383')
        mock_time.return_value = storage_settings.PING_TIMEOUT + 1
        res = self.app.get(
            self.project.api_url_for('osf_storage_hgrid_contents'),
            auth=self.project.creator.auth,
        )
        assert_equal(len(res.json), 1)

    def test_hgrid_contents_tree_not_found_root_path(self):
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_hgrid_contents',
            ),
            auth=self.project.creator.auth,
        )
        assert_equal(res.json, [])

    def test_hgrid_contents_tree_not_found_nested_path(self):
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_hgrid_contents',
                path='not/found',
            ),
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)


class HookTestCase(StorageTestCase):

    def send_hook(self, view_name, payload, signature, path=None,
                  method='put_json', **kwargs):
        method = getattr(self.app, method)
        return method(
            self.project.api_url_for(view_name, path=path),
            payload,
            headers={
                storage_settings.SIGNATURE_HEADER_KEY: signature,
            },
            **kwargs
        )


class TestStartHook(HookTestCase):

    def setUp(self):
        super(TestStartHook, self).setUp()
        self.path = u'söggy/pizza.png'
        self.uploadSignature = '07235a8'
        self.payload = {
            'uploadSignature': self.uploadSignature,
            'uploadPayload': {'extra': {'user': self.user._id}},
        }
        _, self.signature = utils.webhook_signer.sign_payload(self.payload)

    def send_start_hook(self, payload, signature, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_start_hook',
            payload, signature, path,
            **kwargs
        )

    def test_start_hook(self):
        res = self.send_start_hook(
            payload=self.payload, signature=self.signature, path=self.path,
        )
        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        self.node_settings.reload()
        assert_true(self.node_settings.file_tree)
        record = model.OsfStorageFileRecord.find_by_path(self.path, self.node_settings)
        assert_true(record)
        assert_equal(len(record.versions), 1)
        assert_true(record.versions[0].pending)

    def test_start_hook_invalid_signature(self):
        res = self.send_start_hook(
            payload=self.payload, signature='invalid', path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['code'], 400)

    def test_start_hook_path_locked(self):
        record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        record.create_pending_version(self.user, '4217713')
        res = self.send_start_hook(
            payload=self.payload, signature=self.signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 409)
        assert_equal(res.json['code'], 409)
        record.reload()
        assert_equal(len(record.versions), 1)

    def test_start_hook_signature_consumed(self):
        record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        record.create_pending_version(self.user, self.uploadSignature)
        record.resolve_pending_version(
            self.uploadSignature,
            factories.generic_location,
            {
                'size': 1024,
                'content_type': 'text/plain',
                'date_modified': datetime.datetime.utcnow().isoformat(),
            },
        )
        res = self.send_start_hook(
            payload=self.payload, signature=self.signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['code'], 400)
        record.reload()
        assert_equal(len(record.versions), 1)


class TestArchivedHook(HookTestCase):

    def setUp(self):
        super(TestArchivedHook, self).setUp()
        self.path = 'greasy/pízza.png'
        self.size = 1024
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.uploadSignature = '07235a8'
        self.payload = {
            'uploadSignature': self.uploadSignature,
            'metadata': {'archive': 'glacier'},
        }
        _, self.signature = utils.webhook_signer.sign_payload(self.payload)

    def send_archived_hook(self, payload=None, signature=None, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_archived_hook',
            payload=payload or self.payload,
            signature=signature or self.signature,
            path=path or self.path,
            method='put_json',
            **kwargs
        )

    def test_archived(self):
        version = factories.FileVersionFactory(signature=self.uploadSignature)
        self.record.versions = [version]
        self.record.save()
        self.send_archived_hook()
        version.reload()
        assert_in('archive', version.metadata)
        assert_equal(version.metadata['archive'], 'glacier')

    def test_archived_record_not_found(self):
        version = factories.FileVersionFactory(signature=self.uploadSignature)
        self.record.versions = [version]
        self.record.save()
        res = self.send_archived_hook(path=self.path + 'not', expect_errors=True)
        assert_equal(res.status_code, 404)
        version.reload()
        assert_not_in('archive', version.metadata)

    def test_archived_version_not_found(self):
        version = factories.FileVersionFactory(signature=self.uploadSignature[::-1])
        self.record.versions = [version]
        self.record.save()
        res = self.send_archived_hook(expect_errors=True)
        assert_equal(res.status_code, 400)
        version.reload()
        assert_not_in('archive', version.metadata)


class TestPingHook(HookTestCase):

    def setUp(self):
        super(TestPingHook, self).setUp()
        self.path = 'flaky/pízza.png'
        self.size = 1024
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.uploadSignature = '07235a8'
        self.payload = {
            'uploadSignature': self.uploadSignature,
            'uploadPayload': {'extra': {'user': self.user._id}},
        }
        _, self.signature = utils.webhook_signer.sign_payload(self.payload)

    def send_ping_hook(self, payload=None, signature=None, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_ping_hook',
            payload=payload or self.payload,
            signature=signature or self.signature,
            path=path or self.path,
            method='post_json',
            **kwargs
        )

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_ping_pending(self, mock_time):
        mock_time.return_value = 0
        version = self.record.create_pending_version(self.user, self.uploadSignature)
        assert_equal(version.last_ping, 0)
        mock_time.return_value = 10
        res = self.send_ping_hook()
        assert_equal(res.status_code, 200)
        version.reload()
        assert_equal(version.last_ping, 10)

    def test_ping_no_record(self):
        res = self.send_ping_hook(path='missing/file.txt', expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_ping_no_version(self):
        res = self.send_ping_hook(expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_ping_not_pending(self, mock_time):
        version = factories.FileVersionFactory(last_ping=0)
        self.record.versions.append(version)
        self.record.save()
        mock_time.return_value = 10
        res = self.send_ping_hook(expect_errors=True)
        assert_equal(res.status_code, 400)
        version.reload()
        assert_equal(version.last_ping, 0)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_ping_invalid_signature(self, mock_time):
        mock_time.return_value = 0
        version = self.record.create_pending_version(self.user, self.uploadSignature)
        mock_time.return_value = 10
        payload = {
            'uploadSignature': self.uploadSignature[::-1],
            'uploadPayload': {'extra': {'user': self.user._id}},
        }
        _, signature = utils.webhook_signer.sign_payload(payload)
        res = self.send_ping_hook(
            payload=payload, signature=signature,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        version.reload()
        assert_equal(version.last_ping, 0)


class TestSetCachedHook(HookTestCase):

    def setUp(self):
        super(TestSetCachedHook, self).setUp()
        self.path = u'crispy/pízza.png'
        self.size = 1024
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.uploadSignature = '07235a8'
        self.payload = {
            'uploadSignature': self.uploadSignature,
        }
        _, self.signature = utils.webhook_signer.sign_payload(self.payload)

    def send_set_cached_hook(self, payload=None, signature=None, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_cached_hook',
            payload=payload or self.payload,
            signature=signature or self.signature,
            path=path or self.path,
            method='put_json',
            **kwargs
        )

    def test_set_cached_uploading(self):
        version = self.record.create_pending_version(self.user, self.uploadSignature)
        res = self.send_set_cached_hook()
        version.reload()
        assert_equal(version.status, model.status_map['CACHED'])

    def test_set_cached_not_uploading_raises_error(self):
        version = factories.FileVersionFactory(status=model.status_map['CACHED'])
        self.record.versions.append(version)
        self.record.save()
        res = self.send_set_cached_hook(expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_set_cached_no_versions_raises_error(self):
        res = self.send_set_cached_hook(expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_set_cached_no_record_raises_error(self):
        res = self.send_set_cached_hook(path='the/invisible/man.mp3', expect_errors=True)
        assert_equal(res.status_code, 404)


class TestFinishHook(HookTestCase):

    def setUp(self):
        super(TestFinishHook, self).setUp()
        self.path = u'crünchy/pizza.png'
        self.size = 1024
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.uploadSignature = '07235a8'

    def send_finish_hook(self, payload, signature, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_finish_hook',
            payload, signature, path,
            **kwargs
        )

    def make_payload(self, **kwargs):
        payload = {
            'status': 'success',
            'uploadSignature': self.uploadSignature,
            'location': factories.generic_location,
            'metadata': {
                'size': self.size,
                'content_type': 'text/plain',
                'date_modified': '2014-11-06 22:59',
            },
        }
        payload.update(kwargs)
        return payload

    def test_finish_hook_status_success(self):
        payload = self.make_payload()
        message, signature = utils.webhook_signer.sign_payload(payload)
        self.record.create_pending_version(self.user, self.uploadSignature)
        version = self.record.versions[0]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
        )
        assert_equal(res.status_code, 200)
        version.reload()
        assert_false(version.pending)
        assert_equal(version.size, self.size)

    def test_finish_hook_status_error_first_version(self):
        payload = self.make_payload(status='error')
        message, signature = utils.webhook_signer.sign_payload(payload)
        self.record.create_pending_version(self.user, self.uploadSignature)
        version = self.record.versions[-1]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
        )
        assert_equal(res.status_code, 200)
        model.OsfStorageFileRecord._clear_caches()
        model.OsfStorageFileVersion._clear_caches()
        record_reloaded = model.OsfStorageFileRecord.load(self.record._id)
        version_reloaded = model.OsfStorageFileVersion.load(version._id)
        assert_is(record_reloaded, None)
        assert_is(version_reloaded, None)

    def test_finish_hook_status_error_second(self):
        payload = self.make_payload(status='error')
        message, signature = utils.webhook_signer.sign_payload(payload)
        self.record.versions.append(factories.FileVersionFactory())
        self.record.create_pending_version(self.user, self.uploadSignature)
        version = self.record.versions[-1]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
        )
        assert_equal(res.status_code, 200)
        model.OsfStorageFileRecord._clear_caches()
        model.OsfStorageFileVersion._clear_caches()
        record_reloaded = model.OsfStorageFileRecord.load(self.record._id)
        version_reloaded = model.OsfStorageFileVersion.load(version._id)
        assert_true(record_reloaded)
        assert_equal(len(record_reloaded.versions), 1)
        assert_is(version_reloaded, None)

    def test_finish_hook_status_unknown(self):
        payload = self.make_payload(status='pizza')
        message, signature = utils.webhook_signer.sign_payload(payload)
        self.record.create_pending_version(self.user, self.uploadSignature)
        version = self.record.versions[0]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_short'], 'Invalid status')
        version.reload()
        assert_true(version.pending)

    def test_finish_hook_invalid_signature(self):
        payload = self.make_payload()
        message, signature = utils.webhook_signer.sign_payload(payload)
        self.record.create_pending_version(self.user, self.uploadSignature)
        version = self.record.versions[0]
        res = self.send_finish_hook(
            payload=payload, signature=signature[::-1], path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_short'], 'Invalid signature')
        version.reload()
        assert_true(version.pending)

    def test_finish_hook_record_not_found(self):
        payload = self.make_payload()
        message, signature = utils.webhook_signer.sign_payload(payload)
        res = self.send_finish_hook(
            payload=payload, signature=signature, path='missing/pizza.png',
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)

    def test_finish_hook_status_success_no_upload_pending(self):
        payload = self.make_payload()
        message, signature = utils.webhook_signer.sign_payload(payload)
        version = factories.FileVersionFactory()
        self.record.versions.append(version)
        self.record.save()
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_short'], 'No pending upload')

    def test_finish_hook_status_error_no_upload_pending(self):
        payload = self.make_payload(status='error')
        message, signature = utils.webhook_signer.sign_payload(payload)
        version = factories.FileVersionFactory()
        self.record.versions.append(version)
        self.record.save()
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_short'], 'No pending upload')

    def test_finish_hook_status_success_already_complete(self):
        payload = self.make_payload(uploadSignature=self.uploadSignature[::-1])
        message, signature = utils.webhook_signer.sign_payload(payload)
        version = factories.FileVersionFactory()
        self.record.create_pending_version(self.user, self.uploadSignature)
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_short'], 'Invalid upload signature')

    def test_finish_hook_status_error_already_complete(self):
        payload = self.make_payload(
            status='error',
            uploadSignature=self.uploadSignature[::-1],
        )
        message, signature = utils.webhook_signer.sign_payload(payload)
        version = factories.FileVersionFactory()
        self.record.create_pending_version(self.user, self.uploadSignature)
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_short'], 'Invalid upload signature')


class TestUploadFile(StorageTestCase):

    def setUp(self):
        super(TestUploadFile, self).setUp()
        self.name = u'red-specíal.png'
        self.size = 1024
        self.content_type = 'image/png'

    def request_upload_url(self, name, size, content_type, path=None, **kwargs):
        return self.app.post_json(
            self.project.api_url_for(
                'osf_storage_request_upload_url',
                path=path,
            ),
            {
                'name': name,
                'size': size,
                'type': content_type,
            },
            auth=self.project.creator.auth,
            **kwargs
        )

    @mock.patch('website.addons.osfstorage.utils.get_upload_url')
    def test_request_upload_url_without_path(self, mock_get_url):
        mock_get_url.return_value = 'http://brian.queen.com/'
        res = self.request_upload_url(self.name, self.size, self.content_type)
        mock_get_url.assert_called_with(
            self.project,
            self.user,
            self.size,
            self.content_type,
            self.name,
        )
        assert_equal(res.status_code, 200)
        # Response wraps URL in quotation marks
        assert_equal(res.body.strip('"'), mock_get_url.return_value)

    @mock.patch('website.addons.osfstorage.utils.get_upload_url')
    def test_request_upload_url_with_path(self, mock_get_url):
        mock_get_url.return_value = 'http://brian.queen.com/'
        res = self.request_upload_url(self.name, self.size, self.content_type, path='instruments')
        self.project.reload()
        mock_get_url.assert_called_with(
            self.project,
            self.user,
            self.size,
            self.content_type,
            'instruments/' + self.name,
        )

    @mock.patch('website.addons.osfstorage.utils.get_upload_url')
    def test_request_upload_url_too_large(self, mock_get_url):
        mock_get_url.return_value = 'http://brian.queen.com/'
        max_size = settings.ADDONS_AVAILABLE_DICT['osfstorage'].max_file_size
        size = max_size * 1024 * 1024 + 1
        res = self.request_upload_url(
            self.name, size, self.content_type, path='instruments',
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)

    def test_request_upload_url_missing_args(self):
        res = self.app.post_json(
            self.project.api_url_for('osf_storage_request_upload_url'),
            {'name': 'red-special.png'},
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)


class TestViewFile(StorageTestCase):

    def setUp(self):
        super(TestViewFile, self).setUp()
        self.path = 'kind/of/magic.mp3'
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.version = factories.FileVersionFactory()
        self.record.versions.append(self.version)
        self.record.save()

    def view_file(self, path, **kwargs):
        return self.app.get(
            self.project.web_url_for('osf_storage_view_file', path=path),
            auth=self.project.creator.auth,
            **kwargs
        )

    def test_view_file_creates_guid_if_none_exists(self):
        n_objs = model.OsfStorageGuidFile.find().count()
        res = self.view_file(self.path)
        assert_equal(n_objs + 1, model.OsfStorageGuidFile.find().count())
        assert_equal(res.status_code, 302)
        file_obj = model.OsfStorageGuidFile.find_one(node=self.project, path=self.path)
        redirect_parsed = urlparse.urlparse(res.location)
        assert_equal(redirect_parsed.path.strip('/'), file_obj._id)

    def test_view_file_does_not_create_guid_if_exists(self):
        _ = self.view_file(self.path)
        n_objs = model.OsfStorageGuidFile.find().count()
        res = self.view_file(self.path)
        assert_equal(n_objs, model.OsfStorageGuidFile.find().count())

    def test_view_file_deleted_throws_error(self):
        self.record.delete(self.auth_obj, log=False)
        res = self.view_file(self.path, expect_errors=True)
        assert_equal(res.status_code, 410)

    @mock.patch('website.addons.osfstorage.utils.render_file')
    def test_view_file_escapes_html_in_name(self, mock_render):
        mock_render.return_value = 'mock'
        path = 'kind/of/<strong>magic.mp3'
        record = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        version = factories.FileVersionFactory()
        record.versions.append(version)
        record.save()
        res = self.view_file(path).follow(auth=self.project.creator.auth)
        assert markupsafe.escape(record.name) in res


class TestGetRevisions(StorageTestCase):

    def setUp(self):
        super(TestGetRevisions, self).setUp()
        self.path = 'tie/your/mother/down.mp3'
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.record.versions = [factories.FileVersionFactory() for _ in range(15)]
        self.record.save()

    def get_revisions(self, path=None, page=None, **kwargs):
        return self.app.get(
            self.project.api_url_for(
                'osf_storage_get_revisions',
                path=path or self.path,
                page=page,
            ),
            auth=self.user.auth,
            **kwargs
        )

    def test_get_revisions_page_specified(self):
        res = self.get_revisions(path=self.path, page=1)
        expected = [
            utils.serialize_revision(
                self.project,
                self.record,
                self.record.versions[idx - 1],
                idx
            )
            for idx in range(5, 0, -1)
        ]
        assert_equal(res.json['revisions'], expected)
        assert_equal(res.json['more'], False)

    def test_get_revisions_page_not_specified(self):
        res = self.get_revisions(path=self.path)
        expected = [
            utils.serialize_revision(
                self.project,
                self.record,
                self.record.versions[idx - 1],
                idx
            )
            for idx in range(15, 5, -1)
        ]
        assert_equal(res.json['revisions'], expected)
        assert_equal(res.json['more'], True)

    def test_get_revisions_invalid_page(self):
        res = self.get_revisions(path=self.path, page='pizza', expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_get_revisions_path_not_found(self):
        res = self.get_revisions(path='missing', expect_errors=True)
        assert_equal(res.status_code, 404)


class TestDownloadFile(StorageTestCase):

    def setUp(self):
        super(TestDownloadFile, self).setUp()
        self.path = u'tie/your/mother/döwn.mp3'
        self.record = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.version = factories.FileVersionFactory()
        self.record.versions.append(self.version)
        self.record.save()

    def download_file(self, path, version=None, **kwargs):
        return self.app.get(
            self.project.web_url_for(
                'osf_storage_view_file',
                path=path,
                version=version,
                action='download',
            ),
            auth=self.project.creator.auth,
            **kwargs
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        deltas = [
            Delta(
                lambda: self.record.get_download_count(),
                lambda value: value + 1
            ),
            Delta(
                lambda: self.record.get_download_count(len(self.record.versions)),
                lambda value: value + 1
            ),
        ]
        with AssertDeltas(deltas):
            res = self.download_file(self.path)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, mock_get_url.return_value)
        mock_get_url.assert_called_with(
            len(self.record.versions),
            self.version,
            self.record,
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_render_mode(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        deltas = [
            Delta(
                lambda: self.record.get_download_count(),
                lambda value: value
            ),
            Delta(
                lambda: self.record.get_download_count(len(self.record.versions)),
                lambda value: value
            ),
        ]
        with AssertDeltas(deltas):
            res = self.app.get(
                self.project.web_url_for(
                    'osf_storage_view_file',
                    path=self.path,
                    action='download',
                    mode='render',
                ),
                auth=self.project.creator.auth,
            )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_by_version_latest(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        versions = [factories.FileVersionFactory() for _ in range(3)]
        self.record.versions.extend(versions)
        self.record.save()
        deltas = [
            Delta(
                lambda: self.record.get_download_count(),
                lambda value: value + 1
            ),
            Delta(
                lambda: self.record.get_download_count(3),
                lambda value: value + 1
            ),
        ]
        with AssertDeltas(deltas):
            res = self.download_file(path=self.path, version=3)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, mock_get_url.return_value)
        mock_get_url.assert_called_with(3, versions[1], self.record)

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_invalid_version(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        deltas = [
            Delta(
                lambda: self.record.get_download_count(),
                lambda value: value
            ),
            Delta(
                lambda: self.record.get_download_count(3),
                lambda value: value
            ),
        ]
        with AssertDeltas(deltas):
            res = self.download_file(
                path=self.path, version=3,
                expect_errors=True,
            )
        assert_equal(res.status_code, 404)
        assert_false(mock_get_url.called)

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_pending_version(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        self.record.create_pending_version(self.user, '9d989e8')
        deltas = [
            Delta(
                lambda: self.record.get_download_count(),
                lambda value: value
            ),
            Delta(
                lambda: self.record.get_download_count(2),
                lambda value: value
            ),
        ]
        with AssertDeltas(deltas):
            res = self.download_file(
                path=self.path, version=2,
                expect_errors=True,
            )
        assert_equal(res.status_code, 404)
        assert_in('File upload in progress', res)
        assert_false(mock_get_url.called)

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_deleted_version(self, mock_get_url):
        self.record.delete(self.auth_obj, log=False)
        res = self.download_file(self.path, expect_errors=True)
        assert_equal(res.status_code, 410)


class TestDeleteFile(StorageTestCase):

    def test_delete_file(self):
        path = 'going/slightly/mad.mp3'
        record = create_record_with_version(
            path,
            self.node_settings,
            status=model.status_map['COMPLETE'],
        )
        assert_false(record.is_deleted)
        res = self.app.delete(
            self.project.api_url_for(
                'osf_storage_delete_file',
                path=path,
            ),
            auth=self.project.creator.auth,
        )
        assert_equal(res.json['status'], 'success')
        record.reload()
        assert_true(record.is_deleted)

    def test_delete_file_already_deleted(self):
        path = 'going/slightly/mad.mp3'
        record = create_record_with_version(
            path,
            self.node_settings,
            status=model.status_map['COMPLETE'],
        )
        record.delete(self.auth_obj)
        record.save()
        assert_true(record.is_deleted)
        res = self.app.delete(
            self.project.api_url_for(
                'osf_storage_delete_file',
                path=path,
            ),
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['code'], 404)
        record.reload()
        assert_true(record.is_deleted)

    def test_delete_file_not_found(self):
        res = self.app.delete(
            self.project.api_url_for(
                'osf_storage_delete_file',
                path='im/not/there.avi',
            ),
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['code'], 404)


def assert_urls_equal(url1, url2):
    furl1 = furl.furl(url1)
    furl2 = furl.furl(url2)
    for attr in ['scheme', 'host', 'port']:
        setattr(furl1, attr, None)
        setattr(furl2, attr, None)
    assert_equal(furl1, furl2)


class TestLegacyViews(StorageTestCase):

    def setUp(self):
        super(TestLegacyViews, self).setUp()
        self.path = 'mercury.png'

    def test_view_file_redirect(self):
        url = '/{0}/osffiles/{1}/'.format(self.project._id, self.path)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'osf_storage_view_file',
            path=self.path,
        )
        assert_urls_equal(res.location, expected_url)

    def test_download_file_redirect(self):
        url = '/{0}/osffiles/{1}/download/'.format(self.project._id, self.path)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'osf_storage_view_file',
            path=self.path,
            action='download',
        )
        assert_urls_equal(res.location, expected_url)

    def test_download_file_version_redirect(self):
        url = '/{0}/osffiles/{1}/version/3/download/'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'osf_storage_view_file',
            path=self.path,
            action='download',
            version=3,
        )
        assert_urls_equal(res.location, expected_url)

    def test_api_download_file_redirect(self):
        url = '/api/v1/project/{0}/osffiles/{1}/'.format(self.project._id, self.path)
        res = self.app.get(url, auth=self.user.auth)
        print(res.location)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'osf_storage_view_file',
            path=self.path,
            action='download',
        )
        assert_urls_equal(res.location, expected_url)

    def test_api_download_file_version_redirect(self):
        url = '/api/v1/project/{0}/osffiles/{1}/version/3/'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'osf_storage_view_file',
            path=self.path,
            action='download',
            version=3,
        )
        assert_urls_equal(res.location, expected_url)
