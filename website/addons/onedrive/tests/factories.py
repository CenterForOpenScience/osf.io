# -*- coding: utf-8 -*-
"""Factory boy factories for the OneDrive addon."""
import datetime

from dateutil.relativedelta import relativedelta

from factory import SubFactory, Sequence
from tests.factories import (
    ModularOdmFactory,
    UserFactory,
    ProjectFactory,
    ExternalAccountFactory)

from website.addons.onedrive.model import (
    OneDriveUserSettings,
    OneDriveNodeSettings,
)


class OneDriveAccountFactory(ExternalAccountFactory):
    provider = 'onedrive'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.datetime.now() + relativedelta(days=1)

class OneDriveUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = OneDriveUserSettings

    owner = SubFactory(UserFactory)


class OneDriveNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = OneDriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(OneDriveUserSettingsFactory)
    folder_id = '1234567890'
    folder_path = 'Drive/Camera Uploads'
