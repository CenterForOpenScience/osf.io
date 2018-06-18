import mock
import pytest

from tests.base import OsfTestCase
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.nextcloud.tests.factories import NextcloudAccountFactory
from addons.nextcloud.serializer import NextcloudSerializer

pytestmark = pytest.mark.django_db

class TestNextcloudSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'nextcloud'
    Serializer = NextcloudSerializer
    ExternalAccountFactory = NextcloudAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_credentials = mock.patch('addons.nextcloud.serializer.NextcloudSerializer.credentials_are_valid')
        self.mock_credentials.return_value = True
        self.mock_credentials.start()
        super(TestNextcloudSerializer, self).setUp()

    def tearDown(self):
        self.mock_credentials.stop()
        super(TestNextcloudSerializer, self).tearDown()
