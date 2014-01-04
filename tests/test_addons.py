"""

"""

import unittest
from nose.tools import *

from website.addons.base import AddonConfig, AddonSettingsBase


class TestAddonConfig(unittest.TestCase):

    def setUp(self):
        self.addon_config = AddonConfig(
            AddonSettingsBase, 'test', 'test', False, []
        )

    def test_static_url_relative(self):
        url = self.addon_config._static_url('foo')
        assert_equal(
            url,
            '/addons/static/test/foo'
        )

    def test_static_url_absolute(self):
        url = self.addon_config._static_url('/foo')
        assert_equal(
            url,
            '/foo'
        )
