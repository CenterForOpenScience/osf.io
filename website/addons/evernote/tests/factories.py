# -*- coding: utf-8 -*-
"""Factory boy factories for the Evernote addon."""
import mock
from datetime import datetime
from dateutil.relativedelta import relativedelta

from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.evernote.model import (
    EvernoteUserSettings,
    EvernoteNodeSettings
)

class EvernoteAccountFactory(ExternalAccountFactory):
    provider = 'evernote'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    expires_at = datetime.now() + relativedelta(seconds=3600)


class EvernoteUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = EvernoteUserSettings

    owner = SubFactory(UserFactory)


class EvernoteNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = EvernoteNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(EvernoteUserSettingsFactory)
    # with mock.patch('website.addons.evernote.model.EvernoteNodeSettings.fetch_folder_name') as mock_folder:
    #     mock_folder.return_value = 'Camera Uploads'