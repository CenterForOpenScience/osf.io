# -*- coding: utf-8 -*-
"""Factory boy factories for the figshare addon."""
import mock
from datetime import datetime
from dateutil.relativedelta import relativedelta

from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.figshare.model import (
    FigshareUserSettings,
    FigshareNodeSettings
)

class FigshareAccountFactory(ExternalAccountFactory):
    provider = 'figshare'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    expires_at = datetime.now() + relativedelta(seconds=3600)


class FigshareUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = FigshareUserSettings

    owner = SubFactory(UserFactory)


class FigshareNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = FigshareNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(FigshareUserSettingsFactory)
    with mock.patch('website.addons.figshare.model.FigshareNodeSettings.fetch_folder_name') as mock_folder:
        mock_folder.return_value = 'Camera Uploads'
