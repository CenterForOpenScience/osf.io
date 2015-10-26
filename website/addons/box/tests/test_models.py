# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase

from website.addons.box.tests.factories import (
    BoxUserSettingsFactory,
    BoxNodeSettingsFactory,
    BoxAccountFactory
)
from website.addons.box.model import BoxNodeSettings

from website.addons.base.testing import models


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'box'
    full_name = 'Box'
    ExternalAccountFactory = BoxAccountFactory

    NodeSettingsFactory = BoxNodeSettingsFactory
    NodeSettingsClass = BoxNodeSettings
    UserSettingsFactory = BoxUserSettingsFactory

    @mock.patch("website.addons.box.model.refresh_oauth_key")
    def test_serialize_credentials(self, mock_refresh):
        mock_refresh.return_value = True
        super(TestNodeSettings, self).test_serialize_credentials()

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'box'
    full_name = 'Box'
    ExternalAccountFactory = BoxAccountFactory
