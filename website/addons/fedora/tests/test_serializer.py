import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.fedora.tests.factories import FedoraAccountFactory
from website.addons.fedora.serializer import FedoraSerializer

from tests.base import OsfTestCase


class TestFedoraSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'fedora'
    Serializer = FedoraSerializer
    ExternalAccountFactory = FedoraAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_credentials = mock.patch('website.addons.fedora.serializer.FedoraSerializer.credentials_are_valid')
        self.mock_credentials.return_value = True
        self.mock_credentials.start()
        super(TestFedoraSerializer, self).setUp()

    def tearDown(self):
        self.mock_credentials.stop()
        super(TestFedoraSerializer, self).tearDown()
