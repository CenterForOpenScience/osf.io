# -*- coding: utf-8 -*-
"""NodeLogger tests for the Dataverse addon."""
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.logger import StorageAddonNodeLoggerTestSuiteMixin
from website.addons.dataverse.utils import DataverseNodeLogger

from tests.base import OsfTestCase


class TestDataverseNodeLogger(StorageAddonNodeLoggerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'dataverse'

    NodeLogger = DataverseNodeLogger

    def setUp(self):
        super(TestDataverseNodeLogger, self).setUp()
        node_settings = self.node.get_addon(self.addon_short_name)
        node_settings.dataset = 'fake dataset'
        node_settings.save()

    def tearDown(self):
        super(TestDataverseNodeLogger, self).tearDown()

