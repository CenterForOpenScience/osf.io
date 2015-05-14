import requests
import json
import celery
from celery.result import AsyncResult, GroupResult
from faker import Faker

import mock  # noqa
from nose.tools import *  # noqa PEP8 asserts
import httpretty

from framework.auth import Auth

from framework import archiver
from framework.archiver.tasks import *  # noqa
from framework.archiver import (
    ARCHIVER_CHECKING,
    ARCHIVER_PENDING,
    ARCHIVER_SUCCESS
)
from framework.archiver import settings as archiver_settings
from framework.archiver import exceptions as archiver_exceptions
from framework.archiver import utils as archiver_utils

from website import settings
from website.util import waterbutler_url_for
from website.addons.base import StorageAddonBase

from tests import factories
from tests.base import OsfTestCase

fake = Faker()

FILE_TREE = {
    'path': '/',
    'name': '',
    'kind': 'folder',
    'children': [
        {
            'path': '/1234567',
            'name': 'Afile.file',
            'kind': 'file',
            'size': '128',
        },
        {
            'path': '/qwerty',
            'name': 'A Folder',
            'kind': 'folder',
            'children': [
                {
                    'path': '/qwerty/asdfgh',
                    'name': 'coolphoto.png',
                    'kind': 'file',
                    'size': '256',
                }
            ],
        }
    ],
}

class ArchiverTestCase(OsfTestCase):
    def setUp(self):
        super(ArchiverTestCase, self).setUp()
        self.user = factories.UserFactory()
        self.auth = Auth(user=self.user)
        self.src = factories.NodeFactory(creator=self.user)
        self.src.add_addon('dropbox', auth=self.auth)
        self.dst = factories.RegistrationFactory(user=self.user, project=self.src, send_signals=False)
        self.stat_result = stat_file_tree('dropbox', FILE_TREE, self.user)
        self.pks = (self.src._id, self.dst._id, self.user._id)

class TestStorageAddonBase(ArchiverTestCase):

    RESP_MAP = {
        '/': dict(data=FILE_TREE['children']),
        '/1234567': dict(data=FILE_TREE['children'][0]),
        '/qwerty': dict(data=FILE_TREE['children'][1]['children']),
        '/qwerty/asdfgh': dict(data=FILE_TREE['children'][1]['children'][0]),
    }

    @httpretty.activate
    def _test__get_file_tree(self, addon_short_name):
        requests_made = []
        def callback(request, uri, headers):
            path = request.querystring['path'][0]
            requests_made.append(path)
            return (200, headers, json.dumps(self.RESP_MAP[path]))

        for path in self.RESP_MAP.keys():
            url = waterbutler_url_for(
                'metadata',
                provider=addon_short_name,
                path=path,
                node=self.src,
                user=self.user,
                view_only=True,
            )
            httpretty.register_uri(httpretty.GET,
                                   url,
                                   body=callback,
                                   content_type='applcation/json')
        addon = self.src.get_or_add_addon(addon_short_name, auth=self.auth)
        root = {
            'path': '/',
            'name': '',
            'kind': 'folder',
        }
        file_tree = addon._get_file_tree(root, self.user)
        assert_equal(FILE_TREE, file_tree)
        assert_equal(requests_made, ['/', '/qwerty'])  # no requests made for files

    def _test_addon(self, addon_short_name):
        self._test__get_file_tree(addon_short_name)

    def test_addons(self):
        #  Test that each addon in settings.ADDONS_ARCHIVABLE implements the StorageAddonBase interface
        for addon in settings.ADDONS_ARCHIVABLE:
            self._test_addon(addon)

class TestArchiverTasks(ArchiverTestCase):

    def test_archive(self):
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(stat_node, 'si') as mock_stat_node:
            with mock.patch.object(archive_node, 's') as mock_archive_node:
                archive(src_pk, dst_pk, user_pk)
        assert(mock_stat_node.called_with(dst_pk, user_pk))
        assert(mock_archive_node.called_with(src_pk, dst_pk, user_pk))
        assert_true(self.dst.archiving)

    def test_stat_node(self):
        src_pk, dst_pk, user_pk = self.pks
        self.src.add_addon('box', auth=self.auth)  # has box, dropbox
        with mock.patch.object(celery, 'group') as mock_group:
            stat_node(src_pk, dst_pk, user_pk)
        stat_dropbox_sig = stat_addon.si('dropbox', src_pk, dst_pk, user_pk)
        stat_box_sig = stat_addon.si('box', src_pk, dst_pk, user_pk)
        assert(mock_group.called_with(stat_dropbox_sig, stat_box_sig))

    def test_stat_addon(self):
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            with mock.patch.object(archiver, 'AggregateStatResult') as MockStat:
                mock_file_tree.return_value = FILE_TREE
                res = stat_addon('dropbox', src_pk,  dst_pk, user_pk)
        assert_equal(self.dst.archived_providers['dropbox']['status'], ARCHIVER_CHECKING)
        src_dropbox = self.src.get_addon('dropbox')
        assert(MockStat.called_with(
            src_dropbox._id,
            'dropbox',
            targets=[stat_file_tree(src_dropbox, FILE_TREE, self.user)]
        ))
        assert_equal(res.target_name, 'dropbox')

    def test_stat_file_tree(self):
        a_stat_result = stat_file_tree('dropbox', FILE_TREE, self.user)
        assert_equal(a_stat_result.disk_usage, 128 + 256)
        assert_equal(a_stat_result.num_files, 2)
        assert_equal(len(a_stat_result.targets), 2)

    def test_archive_node_pass(self):
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            result = stat_node.apply(args=(src_pk, dst_pk, user_pk)).result
        with mock.patch.object(celery, 'group') as mock_group:
            archive_node(result, src_pk, dst_pk, user_pk)
        archive_dropbox_signature = archive_addon.si(
            'dropbox',
            src_pk,
            dst_pk,
            user_pk,
            result
        )
        assert(mock_group.called_with(archive_dropbox_signature))

    def test_archive_node_fail(self):
        archiver_settings.MAX_ARCHIVE_SIZE = 100
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            result = stat_node.apply(args=(src_pk, dst_pk, user_pk)).result
        with mock.patch.object(archiver_exceptions, 'ArchiverSizeExceeded') as MockError:
            archive_node(result, src_pk, dst_pk, user_pk)
        assert(MockError.called_with(
            self.src,
            self.dst,
            self.user,
            result
        ))

    def test_archive_addon(self):
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            result = AggregateStatResult(
                src_pk,
                self.src.title,
                targets=[result.result for result in stat_node.apply(args=(src_pk, dst_pk, user_pk)).result]
            )
        with mock.patch.object(make_copy_request, 'si') as mock_make_copy_request:
            archive_addon('dropbox', src_pk, dst_pk, user_pk, result.targets.values()[0])
        assert_equal(self.dst.archived_providers['dropbox']['status'], ARCHIVER_PENDING)
        cookie = self.user.get_or_create_cookie()
        assert(mock_make_copy_request.called_with(
            dst_pk,
            settings.WATERBUTLER_URL + '/ops/copy',
            data=dict(
                source=dict(
                    cookie=cookie,
                    nid=src_pk,
                    provider='dropbox',
                    path='/',
                ),
                destination=dict(
                    cookie=cookie,
                    nid=dst_pk,
                    provider=archiver_settings.ARCHIVE_PROVIDER,
                    path='/',
                ),
                rename='Archive of DropBox',
            )
        ))

    @httpretty.activate
    def test_make_copy_request_20X(self):
        src_pk, dst_pk, user_pk = self.pks
        def callback_OK(request, uri, headers):
            return (200, headers, json.dumps({}))

        self.dst.archived_providers = {
            'dropbox': {
                'status': ARCHIVER_PENDING
            }
        }
        self.dst.save()
        url = 'http://' + fake.ipv4()
        httpretty.register_uri(httpretty.POST,
                               url,
                               body=callback_OK,
                               content_type='application/json')
        with mock.patch.object(project_signals, 'archive_callback') as mock_callback:
            make_copy_request(dst_pk, url, {
                'source': {
                    'provider': 'dropbox'
                }
            })
        assert_equal(self.dst.archived_providers['dropbox']['status'], ARCHIVER_SUCCESS)
        assert(mock_callback.called_with(self.dst))

    @httpretty.activate
    def test_make_copy_request_error(self):
        error = {'errors': ['BAD REQUEST']}
        src_pk, dst_pk, user_pk = self.pks
        def callback_400(request, uri, headers):
            return (400, headers, json.dumps(error))

        self.dst.archived_providers = {
            'dropbox': {
                'status': ARCHIVER_PENDING
            }
        }
        self.dst.save()

        url = 'http://' + fake.ipv4()
        httpretty.register_uri(httpretty.POST,
                               url,
                               body=callback_400,
                               content_type='application/json')
        with mock.patch.object(archiver_utils, 'catch_archive_addon_error') as mock_catch_error:
            make_copy_request(dst_pk, url, {
                'source': {
                    'provider': 'dropbox'
                }
            })
        assert(mock_catch_error.called_with(self.dst, 'dropbox', error))
