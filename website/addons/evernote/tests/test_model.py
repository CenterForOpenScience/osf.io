# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.evernote.model import EvernoteNodeSettings

from website.addons.base.testing import models

from website.addons.evernote.tests.factories import (
    EvernoteUserSettingsFactory,
    EvernoteNodeSettingsFactory,
    EvernoteAccountFactory
)

from website.addons.base.testing import models

class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'evernote'
    full_name = 'Evernote'

    NodeSettingsFactory = EvernoteNodeSettingsFactory
    NodeSettingsClass = EvernoteNodeSettings
    UserSettingsFactory = EvernoteUserSettingsFactory
    ExternalAccountFactory = EvernoteAccountFactory

    @mock.patch("website.addons.evernote.utils.get_evernote_client")
    @mock.patch("website.addons.evernote.utils.get_notebook")
    def test_set_folder(self, mock_notebook, mock_client):
        mock_client.return_value = None
        mock_notebook.return_value = {'name':'Test Notebook'}

        super(TestNodeSettings, self).test_set_folder()
    

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'evernote'
    full_name = 'Evernote'
    ExternalAccountFactory = EvernoteAccountFactory

