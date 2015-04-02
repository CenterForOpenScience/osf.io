# -*- coding: utf-8 -*-
"""Factory boy factories for the Google Drive addon."""
import datetime

from framework.auth import Auth
from dateutil.relativedelta import relativedelta

from factory import SubFactory, Sequence, post_generation
from tests.factories import (
    ModularOdmFactory,
    UserFactory,
    ProjectFactory,
    ExternalAccountFactory)

from website.addons.googledrive.model import (
    GoogleDriveUserSettings,
    GoogleDriveNodeSettings,
    GoogleDriveGuidFile,
)


class GoogleDriveAccountFactory(ExternalAccountFactory):
    provider = 'googledrive'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.datetime.now() + relativedelta(days=1)

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class GoogleDriveUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveUserSettings

    owner = SubFactory(UserFactory)


class GoogleDriveNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GoogleDriveUserSettingsFactory)
    drive_folder_id = '12345'
    drive_folder_name = 'Folder'
    folder_path = 'Drive/Camera Uploads'


class GoogleDriveFileFactory(ModularOdmFactory):
    FACTORY_FOR = GoogleDriveGuidFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_googledrive_addon(self, created, extracted):
        self.node.add_addon('googledrive', auth=Auth(user=self.node.creator))
        self.node.save()
