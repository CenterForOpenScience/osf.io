#!/usr/bin/env python
# encoding: utf-8

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories

import hashlib
import urlparse

import furl
from cloudstorm import sign

from framework.auth import Auth
from framework.analytics import get_basic_counters

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import settings as osf_storage_settings


def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    record = model.FileRecord.get_or_create(path, node_settings)
    record.versions.append(version)
    record.save()
    return record


class TestHGridViews(OsfTestCase):

    def setUp(self):
        super(TestHGridViews, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')

    def test_hgrid_contents(self):
        path = 'kind/of/magic.mp3'
        model.FileRecord.get_or_create(
            path=path,
            node_settings=self.node_settings,
        )
        version = factories.FileVersionFactory()
        record = model.FileRecord.find_by_path(path, self.node_settings)
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


class HookTestCase(OsfTestCase):

    def setUp(self):
        super(HookTestCase, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        self.auth_obj = Auth(user=self.project.creator)

    def send_hook(self, view_name, payload, signature, path=None, **kwargs):
        return self.app.put_json(
            self.project.api_url_for(view_name, path=path),
            payload,
            headers={
                osf_storage_settings.SIGNATURE_HEADER_KEY: signature,
            },
            **kwargs
        )


class TestStartHook(HookTestCase):

    def setUp(self):
        super(TestStartHook, self).setUp()
        self.path = 'soggy/pizza.png'
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
        record = model.FileRecord.find_by_path(self.path, self.node_settings)
        assert_true(record)
        assert_equal(len(record.versions), 1)
        assert_equal(record.versions[0].status, model.status['PENDING'])

    def test_start_hook_invalid_signature(self):
        res = self.send_start_hook(
            payload=self.payload, signature='invalid', path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['code'], 400)

    def test_start_hook_path_locked(self):
        record = model.FileRecord.get_or_create(self.path, self.node_settings)
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
        record = model.FileRecord.get_or_create(self.path, self.node_settings)
        record.create_pending_version(self.user, self.uploadSignature)
        record.resolve_pending_version(
            self.uploadSignature,
            factories.generic_location,
            {'size': 1024},
        )
        res = self.send_start_hook(
            payload=self.payload, signature=self.signature, path=self.path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['code'], 400)
        record.reload()
        assert_equal(len(record.versions), 1)


class TestFinishHook(HookTestCase):

    def setUp(self):
        super(TestFinishHook, self).setUp()
        self.path = 'crunchy/pizza.png'
        self.size = 1024
        self.record = model.FileRecord.get_or_create(self.path, self.node_settings)
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
            'metadata': {'size': self.size},
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
        assert_equal(version.status, model.status['COMPLETE'])
        assert_equal(version.size, self.size)

    def test_finish_hook_status_error(self):
        payload = self.make_payload(status='error')
        message, signature = utils.webhook_signer.sign_payload(payload)
        self.record.create_pending_version(self.user, self.uploadSignature)
        version = self.record.versions[0]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=self.path,
        )
        assert_equal(res.status_code, 200)
        version.reload()
        assert_equal(version.status, model.status['FAILED'])

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
        assert_equal(res.json['reason'], 'Invalid status')
        version.reload()
        assert_equal(version.status, model.status['PENDING'])

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
        assert_equal(res.json['reason'], 'Invalid signature')
        version.reload()
        assert_equal(version.status, model.status['PENDING'])

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
        assert_equal(res.json['reason'], 'No pending upload')

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
        assert_equal(res.json['reason'], 'No pending upload')

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
        assert_equal(res.json['reason'], 'Invalid upload signature')

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
        assert_equal(res.json['reason'], 'Invalid upload signature')


class TestUploadFile(OsfTestCase):

    def setUp(self):
        super(TestUploadFile, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        # Refresh records from database; necessary for comparing dates
        self.project.reload()
        self.user.reload()

    def request_upload_url(self, name, size, content_type, path=None):
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
        )

    @mock.patch('website.addons.osfstorage.utils.get_upload_url')
    def test_request_upload_url_without_path(self, mock_get_url):
        mock_get_url.return_value = 'http://brian.queen.com/'
        name = 'red-special.png'
        size = 1024
        content_type = 'image/png'
        res = self.request_upload_url(name, size, content_type)
        mock_get_url.assert_called_with(
            self.project,
            self.user,
            size,
            content_type,
            name,
        )
        assert_equal(res.status_code, 200)
        # Response wraps URL in quotation marks
        assert_equal(res.body.strip('"'), mock_get_url.return_value)

    @mock.patch('website.addons.osfstorage.utils.get_upload_url')
    def test_request_upload_url_with_path(self, mock_get_url):
        mock_get_url.return_value = 'http://brian.queen.com/'
        name = 'red-special.png'
        size = 1024
        content_type = 'image/png'
        res = self.request_upload_url(name, size, content_type, path='instruments')
        self.project.reload()
        mock_get_url.assert_called_with(
            self.project,
            self.user,
            size,
            content_type,
            'instruments/' + name,
        )

    def test_request_upload_url_missing_args(self):
        res = self.app.post_json(
            self.project.api_url_for('osf_storage_request_upload_url'),
            {'name': 'red-special.png'},
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)


class TestViewFile(OsfTestCase):

    def setUp(self):
        super(TestViewFile, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')
        self.path = 'kind/of/magic.mp3'
        self.record = model.FileRecord.get_or_create(self.path, self.node_settings)
        self.version = factories.FileVersionFactory()
        self.record.versions.append(self.version)
        self.record.save()

    def view_file(self, path):
        return self.app.get(
            self.project.web_url_for('osf_storage_view_file', path=path),
            auth=self.project.creator.auth,
        )

    def test_view_file_creates_guid_if_none_exists(self):
        n_objs = model.StorageFile.find().count()
        res = self.view_file(self.path)
        assert_equal(n_objs + 1, model.StorageFile.find().count())
        assert_equal(res.status_code, 302)
        file_obj = model.StorageFile.find_one(node=self.project, path=self.path)
        redirect_parsed = urlparse.urlparse(res.location)
        assert_equal(redirect_parsed.path.strip('/'), file_obj._id)

    def test_view_file_does_not_create_guid_if_exists(self):
        _ = self.view_file(self.path)
        n_objs = model.StorageFile.find().count()
        res = self.view_file(self.path)
        assert_equal(n_objs, model.StorageFile.find().count())


class TestGetRevisions(OsfTestCase):

    def setUp(self):
        super(TestGetRevisions, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        self.path = 'tie/your/mother/down.mp3'
        self.record = model.FileRecord.get_or_create(self.path, self.node_settings)
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


class TestDownloadFile(OsfTestCase):

    def setUp(self):
        super(TestDownloadFile, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        self.path = 'tie/your/mother/down.mp3'
        self.record = model.FileRecord.get_or_create(self.path, self.node_settings)
        self.version = factories.FileVersionFactory()
        self.record.versions.append(self.version)
        self.record.save()

    def download_file(self, path, version=None, **kwargs):
        return self.app.get(
            self.project.web_url_for(
                'osf_storage_download_file',
                path=path,
                version=version,
            ),
            auth=self.project.creator.auth,
            **kwargs
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        res = self.download_file(self.path)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, mock_get_url.return_value)
        mock_get_url.assert_called_with(
            len(self.record.versions),
            self.version,
            self.record,
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_by_version_latest(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        versions = [factories.FileVersionFactory() for _ in range(3)]
        self.record.versions.extend(versions)
        self.record.save()
        count_record = utils.get_download_count(self.record, self.project)
        count_version = utils.get_download_count(self.record, self.project, 3)
        res = self.download_file(path=self.path, version=3)
        assert_equal(res.status_code, 302)
        assert_equal(res.location, mock_get_url.return_value)
        mock_get_url.assert_called_with(3, versions[1], self.record)
        assert_equal(
            utils.get_download_count(self.record, self.project),
            count_record + 1,
        )
        assert_equal(
            utils.get_download_count(self.record, self.project, 3),
            count_version + 1,
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_invalid_version(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        count_record = utils.get_download_count(self.record, self.project)
        count_version = utils.get_download_count(self.record, self.project, 3)
        res = self.download_file(
            path=self.path, version=3,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_false(mock_get_url.called)
        assert_equal(
            utils.get_download_count(self.record, self.project),
            count_record,
        )
        assert_equal(
            utils.get_download_count(self.record, self.project, 3),
            count_version,
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_pending_version(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        self.record.create_pending_version(self.user, '9d989e8')
        count_record = utils.get_download_count(self.record, self.project)
        count_version = utils.get_download_count(self.record, self.project, 2)
        res = self.download_file(
            path=self.path, version=2,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_in('File upload in progress', res)
        assert_false(mock_get_url.called)
        assert_equal(
            utils.get_download_count(self.record, self.project),
            count_record,
        )
        assert_equal(
            utils.get_download_count(self.record, self.project, 2),
            count_version,
        )

    @mock.patch('website.addons.osfstorage.utils.get_download_url')
    def test_download_failed_version(self, mock_get_url):
        mock_get_url.return_value = 'http://freddie.queen.com/'
        self.record.create_pending_version(self.user, '9d989e8')
        self.record.cancel_pending_version('9d989e8')
        count_record = utils.get_download_count(self.record, self.project)
        count_version = utils.get_download_count(self.record, self.project, 2)
        res = self.download_file(
            path=self.path, version=2,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_in('File upload failed', res)
        assert_false(mock_get_url.called)
        assert_equal(
            utils.get_download_count(self.record, self.project),
            count_record,
        )
        assert_equal(
            utils.get_download_count(self.record, self.project, 2),
            count_version,
        )


class TestDeleteFile(OsfTestCase):

    def setUp(self):
        super(TestDeleteFile, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.auth_obj = Auth(user=self.user)
        self.node_settings = self.project.get_addon('osfstorage')

    def test_delete_file(self):
        path = 'going/slightly/mad.mp3'
        record = create_record_with_version(
            path,
            self.node_settings,
            status=model.status['COMPLETE'],
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
            status=model.status['COMPLETE'],
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


class TestLegacyViews(OsfTestCase):

    def setUp(self):
        super(TestLegacyViews, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
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
            'osf_storage_download_file',
            path=self.path,
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
            'osf_storage_download_file',
            path=self.path,
            version=3,
        )
        assert_urls_equal(res.location, expected_url)

