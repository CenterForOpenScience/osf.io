# -*- coding: utf-8 -*-
"""Tests for website.addons.box.utils."""
import mock

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth

from website.addons.box.tests.utils import BoxAddonTestCase
from website.addons.box import utils
from website.addons.box.model import BoxNodeSettings

class TestBoxAddonFolder(BoxAddonTestCase):

    @mock.patch.object(BoxNodeSettings, 'fetch_folder_name', lambda self: 'foo')
    def test_works(self):
        folder = utils.box_addon_folder(
            self.node_settings, Auth(self.user))

        assert_true(isinstance(folder, list))
        assert_true(isinstance(folder[0], dict))

    def test_returns_none_unconfigured(self):
        self.node_settings.folder_id = None
        assert_is(utils.box_addon_folder(
            self.node_settings, Auth(self.user)), None)
