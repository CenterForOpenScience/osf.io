# -*- coding: utf-8 -*-
"""Views tests for the Box addon."""
from nose.tools import *  # noqa (PEP8 asserts)
from waffle.testutils import override_flag
from osf import features
import mock
import unittest

from tests.base import OsfTestCase
from addons.base.tests import views as views_testing

from addons.box.tests.utils import (
    BoxAddonTestCase,
    MockBox,
)


import pytest

from addons.base.tests.models import OAuthAddonNodeSettingsTestSuiteMixin
from addons.box.models import NodeSettings
from addons.box.tests import factories
mock_client = MockBox()


@pytest.mark.django_db
class TestBoxNodeSettingsSunsetOauth(BoxAddonTestCase, views_testing.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def setUp(self):
        super().setUp()
        self.mock_refresh = mock.patch('addons.box.models.Provider.refresh_oauth_key')
        self.mock_refresh.return_value = True
        self.mock_refresh.start()

    def tearDown(self):
        super().tearDown()
        self.mock_refresh.stop()

    @mock.patch(
        'addons.box.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_node_settings(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().run()


@pytest.mark.django_db
class TestBoxNodeSettingsSunsetModel(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):
    full_name = 'Box'
    short_name = 'box'

    ExternalAccountFactory = factories.BoxAccountFactory
    NodeSettingsClass = NodeSettings
    NodeSettingsFactory = factories.BoxNodeSettingsFactory
    UserSettingsFactory = factories.BoxUserSettingsFactory

    def setUp(self):
        super().setUp()
        self.mock_data = mock.patch.object(
            NodeSettings,
            '_folder_data',
            return_value=('12235', '/Foo')
        )
        self.mock_data.start()

    def tearDown(self):
        super().tearDown()
        self.mock_data.stop()

    def test_node_settings(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().run()
