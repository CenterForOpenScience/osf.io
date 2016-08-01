# -*- coding: utf-8 -*-
"""Factory boy factories for the OwnCloud addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.owncloud.model import (
    AddonOwnCloudUserSettings,
    AddonOwnCloudNodeSettings
)

class OwnCloudAccountFactory(ExternalAccountFactory):
    provider = 'owncloud'

    provider_id  = Sequence(lambda n: 'https://localhost/{0}/owncloud'.format(n))
    oauth_key = Sequence(lambda n: 'https://localhost/{0}/owncloud'.format(n))
    display_name='catname'
    oauth_secret='meoword'


class OwnCloudUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonOwnCloudUserSettings

    owner = SubFactory(UserFactory)


class OwnCloudNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonOwnCloudNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(OwnCloudUserSettingsFactory)
