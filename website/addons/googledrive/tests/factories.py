# -*- coding: utf-8 -*-
"""Factory boy factories for the Google Drive addon."""
import datetime

from dateutil.relativedelta import relativedelta

from factory import SubFactory, Sequence
from tests.factories import (
    ModularOdmFactory,
    UserFactory,
    ProjectFactory,
    ExternalAccountFactory)

from website.addons.googledrive.model import (
    GoogleDriveUserSettings,
    GoogleDriveNodeSettings,
)


class GoogleDriveAccountFactory(ExternalAccountFactory):
    provider = 'googledrive'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.datetime.now() + relativedelta(days=1)

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class GoogleDriveUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = GoogleDriveUserSettings

    owner = SubFactory(UserFactory)


class GoogleDriveNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = GoogleDriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GoogleDriveUserSettingsFactory)
    folder_id = '1234567890'
    folder_path = 'Drive/Camera Uploads'
