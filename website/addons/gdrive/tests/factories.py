# -*- coding: utf-8 -*-
"""Factory boy factories for the Google Drive addon."""

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.gdrive.model import (
    AddonGdriveUserSettings, AddonGdriveNodeSettings, AddonGdriveGuidFile
)


# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class GdriveUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = AddonGdriveUserSettings

    username = 'name/email Address'
    owner = SubFactory(UserFactory)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))


class GdriveNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = AddonGdriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GdriveUserSettingsFactory)
    folder = 'Camera Uploads'
    waterbutler_folder = {
        'id': '12345',
        'name': 'Camera Uploads',
        'path':'Drive/Camera Uploads'
    }



class GdriveFileFactory(ModularOdmFactory):
    FACTORY_FOR = AddonGdriveGuidFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_gdrive_addon(self, created, extracted):
        self.node.add_addon('gdrive', auth=Auth(user=self.node.creator))
        self.node.save()