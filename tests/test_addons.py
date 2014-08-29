"""

"""

import unittest
from nose.tools import *

from website.addons.base import AddonConfig, AddonNodeSettingsBase


class TestAddonConfig(unittest.TestCase):

    def setUp(self):
        self.addon_config = AddonConfig(
            short_name='test', full_name='test', owners=['node'],
            added_to={'node': False}, categories=[],
            settings_model=AddonNodeSettingsBase,
        )

    def test_static_url_relative(self):
        url = self.addon_config._static_url('foo')
        assert_equal(
            url,
            '/static/addons/test/foo'
        )

    def test_deleted_defaults_to_false(self):
        class MyAddonSettings(AddonNodeSettingsBase):
            pass

        config = MyAddonSettings()
        assert_is(config.deleted, False)

    def test_static_url_absolute(self):
        url = self.addon_config._static_url('/foo')
        assert_equal(
            url,
            '/foo'
        )

    # TODO: Add tests for callbacks - specifically, `on_add()` and `on_delete()`
