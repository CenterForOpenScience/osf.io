# -*- coding: utf-8 -*-
import mock
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.cloudfiles.tests.factories import CloudFilesAccountFactory
from addons.cloudfiles.serializer import CloudFilesSerializer

class CloudFilesAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'cloudfiles'
    ExternalAccountFactory = CloudFilesAccountFactory
    Serializer = CloudFilesSerializer
    client = None
    folder = {
        'path': 'container',
        'name': 'container',
        'id': 'container'
    }


class MockConnection():
    object_store = type('', (), {'create_container': mock.Mock()})
