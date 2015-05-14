import requests
import json
import celery
from celery.result import AsyncResult, GroupResult

import mock  # noqa
from nose.tools import *  # noqa PEP8 asserts
import httpretty

from framework.auth import Auth

from framework.archiver.tasks import *  # noqa

from website import settings
from website.util import waterbutler_url_for
from website.addons.base import StorageAddonBase

from tests import factories
from tests.base import OsfTestCase

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
        with mock.patch.object(stat_node, 'si') as mock_stat_node:
            with mock.patch.object(archive_node, 's') as mock_archive_node:
                archive(self.src._id, self.dst._id, self.user._id)
        assert(mock_stat_node.called_with(self.src._id, self.user._id))
        assert(mock_archive_node.called_with(self.src._id, self.dst._id, self.user._id))
        assert_true(self.dst.archiving)

    def test_stat_node(self):
        pass
