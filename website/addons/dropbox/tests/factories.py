# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from factory import SubFactory, Sequence
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
