from unittest import mock
import pytest

from tests.base import OsfTestCase
from addons.base.exceptions import NotApplicableError
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.boa.tests.utils import BoaAddonTestCaseBaseMixin

pytestmark = pytest.mark.django_db


class TestBoaSerializer(BoaAddonTestCaseBaseMixin, StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    def set_provider_id(self, pid=None):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_credentials = mock.patch('addons.boa.serializer.BoaSerializer.credentials_are_valid')
        self.mock_credentials.return_value = True
        self.mock_credentials.start()
        super().setUp()

    def tearDown(self):
        self.mock_credentials.stop()
        super().tearDown()

    def test_serialize_settings_authorized_folder_is_set(self):
        self.set_provider_id(pid='foo')
        with pytest.raises(NotApplicableError):
            with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
                _ = self.ser.serialize_settings(self.node_settings, self.user, self.client)
