# -*- coding: utf-8 -*-
"""Factory boy factories for the OwnCloud addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.owncloud.model import (
    OwnCloudUserSettings,
    OwnCloudNodeSettings
)

class OwnCloudAccountFactory(ExternalAccountFactory):
    provider = 'owncloud'
    provider_name='OwnCloud'

    host="https://localhost/owncloud"
    username="johnsmith"
    password="friend"


class OwnCloudUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonOwnCloudUserSettings

    owner = SubFactory(UserFactory)


class OwnCloudNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonOwnCloudNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(OwnCloudUserSettingsFactory)
