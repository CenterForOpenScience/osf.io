# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.dropbox.model import (
    DropboxUserSettings, DropboxNodeSettings
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
