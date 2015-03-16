# -*- coding: utf-8 -*-
"""Factory boy factories for the Google Drive addon."""
from datetime import datetime

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import (
    ModularOdmFactory,
    UserFactory,
    ProjectFactory,
)

from website.addons.googledrive.model import (
    GoogleDriveUserSettings,
    GoogleDriveNodeSettings,
    GoogleDriveOAuthSettings,
    GoogleDriveGuidFile,
)


class GoogleDriveOAuthSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveOAuthSettings

    username = 'Den'
    user_id = 'b4rn311'
    expires_at = datetime(2045, 1, 1)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))
    refresh_token = Sequence(lambda n: 'abcdef{0}'.format(n))


# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class GoogleDriveUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveUserSettings

    owner = SubFactory(UserFactory)
    oauth_settings = SubFactory(GoogleDriveOAuthSettingsFactory)


class GoogleDriveNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GoogleDriveUserSettingsFactory)
    folder_id = '12345'
    folder_path = 'Drive/Camera Uploads'


class GoogleDriveFileFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveGuidFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_googledrive_addon(self, created, extracted):
        self.node.add_addon('googledrive', auth=Auth(user=self.node.creator))
        self.node.save()
