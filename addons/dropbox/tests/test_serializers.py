"""Serializer tests for the Dropbox addon."""
import pytest

from tests.base import OsfTestCase

from addons.dropbox.serializer import DropboxSerializer

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.dropbox.tests.factories import DropboxAccountFactory
from addons.dropbox.tests.utils import MockDropbox


mock_client = MockDropbox()
pytestmark = pytest.mark.django_db


class TestDropboxSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'dropbox'

    ExternalAccountFactory = DropboxAccountFactory
    Serializer = DropboxSerializer
    client = mock_client

    def set_provider_id(self, pid):
        self.node_settings.folder = pid
