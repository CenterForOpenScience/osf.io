# -*- coding: utf-8 -*-
"""Factory boy factories for the Onedrive addon."""
import mock
from datetime import datetime
from dateutil.relativedelta import relativedelta

from framework.auth import Auth

from factory import SubFactory, post_generation, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.onedrive.model import (
    OnedriveUserSettings,
    OnedriveNodeSettings
)

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field


class OnedriveAccountFactory(ExternalAccountFactory):
    provider = 'onedrive'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.now() + relativedelta(seconds=3600)


class OnedriveUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = OnedriveUserSettings

    owner = SubFactory(UserFactory)


class OnedriveNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = OnedriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(OnedriveUserSettingsFactory)
    with mock.patch('website.addons.onedrive.model.OnedriveNodeSettings.fetch_folder_name') as mock_folder:
        mock_folder.return_value = 'Camera Uploads'
