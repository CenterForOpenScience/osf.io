#!/usr/bin/env python
# encoding: utf-8

import mock
from nose.tools import *  # noqa

from framework.auth.core import Auth
from website.addons.osfstorage.tests.utils import (
    StorageTestCase, Delta, AssertDeltas
)
from website.addons.osfstorage.tests import factories

import furl

from framework.auth import signing
from website.util import rubeus

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import views
from website.addons.base.views import make_auth
from website.addons.osfstorage import settings as storage_settings


def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    record = model.OsfStorageFileRecord.get_or_create(path, node_settings)
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

    def test_hgrid_contents(self):
        path = u'kind/of/magíc.mp3'
        record, _ = model.OsfStorageFileRecord.get_or_create(
            path=path,
            node_settings=self.node_settings,
        )
        version = factories.FileVersionFactory()
        record.versions.append(version)
        record.save()
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': 'kind/of/'},
        )
        assert_equal(len(res.json), 1)
        assert_equal(
            res.json[0],
            utils.serialize_metadata_hgrid(
                record,
                self.project,
            )
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

    def test_hgrid_contents_tree_not_found_root_path(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': ''},
        )
        assert_equal(res.json, [])

    def test_hgrid_contents_tree_not_found_nested_path(self):
        res = self.send_hook(
            'osf_storage_get_metadata_hook',
            {'path': 'not/found'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)


class TestUploadFileHook(HookTestCase):

    def setUp(self):
        super(TestUploadFileHook, self).setUp()
        self.path = 'fresh/pízza.png'
        self.record, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.auth = make_auth(self.user)

    def send_upload_hook(self, payload=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_file_hook',
            payload=payload or self.payload,
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
            'metadata': {'provider': 'osfstorage', 'service': 'cloud', 'name': 'file'},
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
        record = model.OsfStorageFileRecord.find_by_path(path, self.node_settings)
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

    # def test_upload_update_deleted(self):
    #     pass


class TestUpdateMetadataHook(HookTestCase):

    def setUp(self):
        super(TestUpdateMetadataHook, self).setUp()
        self.path = 'greasy/pízza.png'
        self.record, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.version = factories.FileVersionFactory()
        self.record.versions = [self.version]
        self.record.save()
        self.payload = {
            'metadata': {'archive': 'glacier'},
            'version': self.version._id,
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
        self.record, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.record.versions = [factories.FileVersionFactory() for __ in range(15)]
        self.record.save()

    def get_revisions(self, path=None, page=None, **kwargs):

        return self.app.get(
            self.project.api_url_for(
                'osf_storage_get_revisions',
                **signing.sign_data(
                    signing.default_signer,
                    {
                        'path': path or self.path,
                        'page': page,
                    }
                )
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


# class TestDownloadFile(StorageTestCase):

#     def setUp(self):
#         super(TestDownloadFile, self).setUp()
#         self.path = u'tie/your/mother/döwn.mp3'
#         self.record, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
#         self.version = factories.FileVersionFactory()
#         self.record.versions.append(self.version)
#         self.record.save()

#     def download_file(self, path, version=None, **kwargs):
#         return self.app.get(
#             self.project.web_url_for(
#                 'addon_view_or_download_file',
#                 path=path,
#                 version=version,
#                 action='download',
#                 provider='osfstorage',
#             ),
#             maybe_follow=True,
#             auth=self.project.creator.auth,
#             **kwargs
#         )

#     @mock.patch('website.addons.osfstorage.utils.requests.get')
#     @mock.patch('website.addons.osfstorage.utils.get_waterbutler_download_url')
#     def test_download(self, mock_get_url, mock_request):
#         file_content = b'I am a teapot!'
#         mock_get_url.return_value = 'http://freddie.queen.com/'
#         mock_request.return_value = mock.Mock(content=file_content)

#         res = self.download_file(self.path)

#         assert_equal(res.status_code, 200)
#         mock_request.assert_called_once_with('http://freddie.queen.com/', allow_redirects=False)
#         assert_equal(res.body, file_content)
#         mock_get_url.assert_called_with(
#             len(self.record.versions),
#             self.version,
#             self.record,
#             mode=None,
#         )

#     @mock.patch('website.addons.osfstorage.utils.requests.get')
#     @mock.patch('website.addons.osfstorage.utils.get_waterbutler_download_url')
#     def test_download_redirect_signed_url(self, mock_get_url, mock_request):
#         mock_get_url.return_value = 'http://freddie.queen.com/'
#         mock_request.return_value = mock.Mock(status_code=302, headers={'Location': 'http://eddiebowy.horse/'})

#         res = self.download_file(self.path)

#         assert_equal(res.status_code, 302)
#         mock_request.assert_called_once_with('http://freddie.queen.com/', allow_redirects=False)
#         assert_equal(res.location, 'http://eddiebowy.horse/')
#         mock_get_url.assert_called_with(
#             len(self.record.versions),
#             self.version,
#             self.record,
#             mode=None,
#         )

#     @mock.patch('website.addons.osfstorage.utils.requests.get')
#     @mock.patch('website.addons.osfstorage.utils.get_waterbutler_download_url')
#     def test_download_render_mode(self, mock_get_url, mock_request):
#         mock_get_url.return_value = 'http://freddie.queen.com/'
#         mock_request.return_value = mock.Mock(status_code=302, headers={'Location': 'http://eddiebowy.horse/'})

#         self.app.get(
#             self.project.web_url_for(
#                 'osf_storage_view_file',
#                 path=self.path,
#                 action='download',
#                 mode='render',
#             ),
#             auth=self.project.creator.auth,
#         )

#         mock_get_url.assert_called_with(
#             len(self.record.versions),
#             self.version,
#             self.record,
#             mode='render',
#         )

#     @mock.patch('website.addons.osfstorage.utils.requests.get')
#     @mock.patch('website.addons.osfstorage.utils.get_waterbutler_download_url')
#     def test_download_by_version_latest(self, mock_get_url, mock_request):
#         mock_get_url.return_value = 'http://freddie.queen.com/'
#         mock_request.return_value = mock.Mock(status_code=302, headers={'Location': 'http://eddiebowy.horse/'})

#         versions = [factories.FileVersionFactory() for _ in range(3)]
#         self.record.versions.extend(versions)
#         self.record.save()
#         res = self.download_file(path=self.path, version=3)

#         assert_equal(res.status_code, 302)
#         assert_equal(res.location, 'http://eddiebowy.horse/')
#         mock_get_url.assert_called_with(3, versions[1], self.record, mode=None)

#     @mock.patch('website.addons.osfstorage.utils.get_waterbutler_download_url')
#     def test_download_invalid_version(self, mock_get_url):
#         mock_get_url.return_value = 'http://freddie.queen.com/'

#         res = self.download_file(
#             path=self.path, version=3,
#             expect_errors=True,
#         )

#         assert_equal(res.status_code, 404)
#         assert_false(mock_get_url.called)

#     @mock.patch('website.addons.osfstorage.utils.get_waterbutler_download_url')
#     def test_download_deleted_version(self, mock_get_url):
#         self.record.delete(self.auth_obj, log=False)
#         res = self.download_file(self.path, expect_errors=True)
#         assert_equal(res.status_code, 410)


def assert_urls_equal(url1, url2):
    furl1 = furl.furl(url1)
    furl2 = furl.furl(url2)
    for attr in ['scheme', 'host', 'port']:
        setattr(furl1, attr, None)
        setattr(furl2, attr, None)
    assert_equal(furl1, furl2)
