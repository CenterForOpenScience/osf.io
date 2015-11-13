# -*- coding: utf-8 -*-
"""Factory boy factories for the OneDrive addon."""

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.onedrive.model import (
    OneDriveUserSettings, OneDriveNodeSettings
)


# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class OneDriveUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = OneDriveUserSettings

    owner = SubFactory(UserFactory)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))


class OneDriveNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = OneDriveNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(OneDriveUserSettingsFactory)
    folder = 'Camera Uploads'
