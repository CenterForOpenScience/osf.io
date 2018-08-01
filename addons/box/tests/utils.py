# -*- coding: utf-8 -*-
import mock
from contextlib import contextmanager

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.box.models import Provider
from addons.box.tests.factories import BoxAccountFactory


class BoxAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'box'
    ExternalAccountFactory = BoxAccountFactory
    Provider = Provider

    def set_node_settings(self, settings):
        super(BoxAddonTestCase, self).set_node_settings(settings)
        settings.folder_id = '1234567890'
        settings.folder_name = 'Foo'

mock_responses = {
    'folder': {
        'name': 'anything',
        'item_collection': {
            'entries': [
                {
                    'name': 'anything', 'type': 'file', 'id': 'anything'
                },
                {
                    'name': 'anything', 'type': 'folder', 'id': 'anything'
                },
                {
                    'name': 'anything', 'type': 'anything', 'id': 'anything'
                },
            ]
        },
        'path_collection': {
            'entries': [
                {
                    'name': 'anything', 'type': 'file', 'id': 'anything'
                },
                {
                    'name': 'anything', 'type': 'folder', 'id': 'anything'
                },
                {
                    'name': 'anything', 'type': 'anything', 'id': 'anything'
                },
            ]
        }
    },
    'put_file': {
        'bytes': 77,
        'icon': 'page_white_text',
        'is_dir': False,
        'mime_type': 'text/plain',
        'modified': 'Wed, 20 Jul 2011 22:04:50 +0000',
        'path': '/magnum-opus.txt',
        'rev': '362e2029684fe',
        'revision': 221922,
        'root': 'box',
        'size': '77 bytes',
        'thumb_exists': False
    },
    'metadata_list': {
        "size": "0 bytes",
        "hash": "37eb1ba1849d4b0fb0b28caf7ef3af52",
        "bytes": 0,
        "thumb_exists": False,
        "rev": "714f029684fe",
        "modified": "Wed, 27 Apr 2011 22:18:51 +0000",
        "path": "/Public",
        "is_dir": True,
        "icon": "folder_public",
        "root": "box",
        "contents": [
            {
                "size": "0 bytes",
                "rev": "35c1f029684fe",
                "thumb_exists": False,
                "bytes": 0,
                "modified": "Mon, 18 Jul 2011 20:13:43 +0000",
                "client_mtime": "Wed, 20 Apr 2011 16:20:19 +0000",
                "path": "/Public/latest.txt",
                "is_dir": False,
                "icon": "page_white_text",
                "root": "box",
                "mime_type": "text/plain",
                "revision": 220191
            },
            {
                'bytes': 0,
                'icon': 'folder',
                'is_dir': True,
                'modified': 'Sat, 22 Mar 2014 05:40:29 +0000',
                'path': '/datasets/New Folder',
                'rev': '3fed51f002c12fc',
                'revision': 67032351,
                'root': 'box',
                'size': '0 bytes',
                'thumb_exists': False
            }
        ],
        "revision": 29007
    },
    'metadata_single': {
        'id': 'id',
        'bytes': 74,
        'client_mtime': 'Mon, 13 Jan 2014 20:24:15 +0000',
        'icon': 'page_white',
        'is_dir': False,
        'mime_type': 'text/csv',
        'modified': 'Fri, 21 Mar 2014 05:46:36 +0000',
        'path': '/datasets/foo.txt',
        'rev': 'a2149fb64',
        'revision': 10,
        'root': 'app_folder',
        'size': '74 bytes',
        'thumb_exists': False
    },
    'revisions': [{'bytes': 0,
                   'client_mtime': 'Wed, 31 Dec 1969 23:59:59 +0000',
                   'icon': 'page_white_picture',
                   'is_deleted': True,
                   'is_dir': False,
                   'mime_type': 'image/png',
                   'modified': 'Tue, 25 Mar 2014 03:39:13 +0000',
                   'path': '/svs-v-barks.png',
                   'rev': '3fed741002c12fc',
                   'revision': 67032897,
                   'root': 'box',
                   'size': '0 bytes',
                   'thumb_exists': True},
                  {'bytes': 151164,
                   'client_mtime': 'Sat, 13 Apr 2013 21:56:36 +0000',
                   'icon': 'page_white_picture',
                   'is_dir': False,
                   'mime_type': 'image/png',
                   'modified': 'Tue, 25 Mar 2014 01:45:51 +0000',
                   'path': '/svs-v-barks.png',
                   'rev': '3fed61a002c12fc',
                   'revision': 67032602,
                   'root': 'box',
                   'size': '147.6 KB',
                   'thumb_exists': True}]
}


class MockBox(object):

    def put_file(self, full_path, file_obj, overwrite=False, parent_rev=None):
        return mock_responses['put_file']

    def metadata(self, path, list=True, file_limit=25000, hash=None, rev=None,
                 include_deleted=False):
        if list:
            ret = mock_responses['metadata_list']
        else:
            ret = mock_responses['metadata_single']
            ret['path'] = path
        return ret

    def folder(*args, **kwargs):
        return mock_responses['folder']

    def get_file_and_metadata(*args, **kwargs):
        pass

    def file_delete(self, path):
        return mock_responses['metadata_single']

    def revisions(self, path):
        ret = mock_responses['revisions']
        for each in ret:
            each['path'] = path
        return ret

    def user(self):
        return {'display_name': 'Mr. Box'}


@contextmanager
def patch_client(target, mock_client=None):
    """Patches a function that returns a Box Client, returning an instance
    of MockBox instead.

    Usage: ::

        with patch_client('addons.box.views.Client') as client:
            # test view that uses the box client.
    """
    with mock.patch(target) as client_getter:
        client = mock_client or MockBox()
        client_getter.return_value = client
        yield client
