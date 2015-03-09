# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.dropbox.model import (
    DropboxUserSettings, DropboxNodeSettings, DropboxFile
)


# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class DropboxUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = DropboxUserSettings

    owner = SubFactory(UserFactory)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))


class DropboxNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = DropboxNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(DropboxUserSettingsFactory)
    folder = 'Camera Uploads'


class DropboxFileFactory(ModularOdmFactory):
    FACTORY_FOR = DropboxFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_dropbox_addon(self, created, extracted):
        self.node.add_addon('dropbox', auth=Auth(user=self.node.creator))
        self.node.save()
