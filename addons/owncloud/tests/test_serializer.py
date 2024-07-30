from unittest import mock
import pytest

from tests.base import OsfTestCase
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.owncloud.tests.utils import OwnCloudAddonTestCaseBaseMixin

pytestmark = pytest.mark.django_db


class TestOwnCloudSerializer(OwnCloudAddonTestCaseBaseMixin, StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    def set_provider_id(self, pid=None):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_credentials = mock.patch('addons.owncloud.serializer.OwnCloudSerializer.credentials_are_valid')
        self.mock_credentials.return_value = True
        self.mock_credentials.start()
        super().setUp()

    def tearDown(self):
        self.mock_credentials.stop()
        super().tearDown()
