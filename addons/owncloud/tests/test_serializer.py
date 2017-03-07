import mock
import pytest

from tests.base import OsfTestCase
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.owncloud.tests.factories import OwnCloudAccountFactory
from addons.owncloud.serializer import OwnCloudSerializer

pytestmark = pytest.mark.django_db

class TestOwnCloudSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'owncloud'
    Serializer = OwnCloudSerializer
    ExternalAccountFactory = OwnCloudAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_credentials = mock.patch('addons.owncloud.serializer.OwnCloudSerializer.credentials_are_valid')
        self.mock_credentials.return_value = True
        self.mock_credentials.start()
        super(TestOwnCloudSerializer, self).setUp()

    def tearDown(self):
        self.mock_credentials.stop()
        super(TestOwnCloudSerializer, self).tearDown()
