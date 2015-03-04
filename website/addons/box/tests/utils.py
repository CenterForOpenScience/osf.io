# -*- coding: utf-8 -*-
import mock
from contextlib import contextmanager

from modularodm import storage

from framework.mongo import set_up_storage

from website.addons.base.testing import AddonTestCase
from website.addons.box import MODELS
from website.addons.box.model import BoxOAuthSettings


def init_storage():
    set_up_storage(MODELS, storage_class=storage.MongoStorage)


class BoxAddonTestCase(AddonTestCase):

    ADDON_SHORT_NAME = 'box'

    def set_user_settings(self, settings):
        self.oauth = BoxOAuthSettings(
            user_id='test', access_token='test')
        self.oauth.save()
        settings.oauth_settings = self.oauth

    def set_node_settings(self, settings):
        settings.folder_id = '1234567890'


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
                u'bytes': 0,
                u'icon': u'folder',
                u'is_dir': True,
                u'modified': u'Sat, 22 Mar 2014 05:40:29 +0000',
                u'path': u'/datasets/New Folder',
                u'rev': u'3fed51f002c12fc',
                u'revision': 67032351,
                u'root': u'box',
                u'size': u'0 bytes',
                u'thumb_exists': False
            }
        ],
        "revision": 29007
    },
    'metadata_single': {
        u'id': 'id',
        u'bytes': 74,
        u'client_mtime': u'Mon, 13 Jan 2014 20:24:15 +0000',
        u'icon': u'page_white',
        u'is_dir': False,
        u'mime_type': u'text/csv',
        u'modified': u'Fri, 21 Mar 2014 05:46:36 +0000',
        u'path': '/datasets/foo.txt',
        u'rev': u'a2149fb64',
        u'revision': 10,
        u'root': u'app_folder',
        u'size': u'74 bytes',
        u'thumb_exists': False
    },
    'revisions': [{u'bytes': 0,
                   u'client_mtime': u'Wed, 31 Dec 1969 23:59:59 +0000',
                   u'icon': u'page_white_picture',
                   u'is_deleted': True,
                   u'is_dir': False,
                   u'mime_type': u'image/png',
                   u'modified': u'Tue, 25 Mar 2014 03:39:13 +0000',
                   u'path': u'/svs-v-barks.png',
                   u'rev': u'3fed741002c12fc',
                   u'revision': 67032897,
                   u'root': u'box',
                   u'size': u'0 bytes',
                   u'thumb_exists': True},
                  {u'bytes': 151164,
                   u'client_mtime': u'Sat, 13 Apr 2013 21:56:36 +0000',
                   u'icon': u'page_white_picture',
                   u'is_dir': False,
                   u'mime_type': u'image/png',
                   u'modified': u'Tue, 25 Mar 2014 01:45:51 +0000',
                   u'path': u'/svs-v-barks.png',
                   u'rev': u'3fed61a002c12fc',
                   u'revision': 67032602,
                   u'root': u'box',
                   u'size': u'147.6 KB',
                   u'thumb_exists': True}]
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

    def get_folder(*args, **kwargs):
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

    def get_user_info(self):
        return {'display_name': 'Mr. Box'}


@contextmanager
def patch_client(target, mock_client=None):
    """Patches a function that returns a BoxClient, returning an instance
    of MockBox instead.

    Usage: ::

        with patch_client('website.addons.box.view.config.get_client') as client:
            # test view that uses the box client.
    """
    with mock.patch(target) as client_getter:
        client = mock_client or MockBox()
        client_getter.return_value = client
        yield client
