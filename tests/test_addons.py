"""

"""

import unittest
from nose.tools import *

from website.addons.base import AddonConfig, AddonNodeSettingsBase


class TestAddonConfig(unittest.TestCase):

    def setUp(self):
        self.addon_config = AddonConfig(
            short_name='test', full_name='test',
            added_by_default=False, categories=[],
            settings_model=AddonNodeSettingsBase,
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
