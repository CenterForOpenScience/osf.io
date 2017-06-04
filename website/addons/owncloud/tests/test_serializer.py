import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.owncloud.tests.factories import OwnCloudAccountFactory
from website.addons.owncloud.serializer import OwnCloudSerializer

from tests.base import OsfTestCase


class TestOwnCloudSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'owncloud'
    Serializer = OwnCloudSerializer
    ExternalAccountFactory = OwnCloudAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_credentials = mock.patch('website.addons.owncloud.serializer.OwnCloudSerializer.credentials_are_valid')
        self.mock_credentials.return_value = True
        self.mock_credentials.start()
        super(TestOwnCloudSerializer, self).setUp()

    def tearDown(self):
        self.mock_credentials.stop()
        super(TestOwnCloudSerializer, self).tearDown()
