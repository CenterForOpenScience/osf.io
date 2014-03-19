# -*- coding: utf-8 -*-

from webtest_plus import TestApp

import website
from website.addons.base.testing import AddonTestCase

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

class DropboxAddonTestCase(AddonTestCase):
    ADDON_SHORT_NAME = 'dropbox'

    def create_app(self):
        return TestApp(app)

    def set_user_settings(self, settings):
        settings.access_token = '12345abc'
        settings.dropbox_id = 'mydropboxid'

    def set_node_settings(self, settings):
        settings.folder = 'foo'

mock_responses = {
    'put_file': {
        'bytes': 77,
        'icon': 'page_white_text',
        'is_dir': False,
        'mime_type': 'text/plain',
        'modified': 'Wed, 20 Jul 2011 22:04:50 +0000',
        'path': '/magnum-opus.txt',
        'rev': '362e2029684fe',
        'revision': 221922,
        'root': 'dropbox',
        'size': '77 bytes',
        'thumb_exists': False
    }
}
