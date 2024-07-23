"""NodeLogger tests for the Dataverse addon."""
import pytest

from addons.base.tests.logger import StorageAddonNodeLoggerTestSuiteMixin
from addons.dataverse.utils import DataverseNodeLogger

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestDataverseNodeLogger(StorageAddonNodeLoggerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'dataverse'

    NodeLogger = DataverseNodeLogger

    def setUp(self):
        super().setUp()
        node_settings = self.node.get_addon(self.addon_short_name)
        node_settings.dataset = 'fake dataset'
        node_settings.save()

    def tearDown(self):
        super().tearDown()
