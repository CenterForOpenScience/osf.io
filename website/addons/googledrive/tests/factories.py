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
    GoogleDriveGuidFile,
)



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
