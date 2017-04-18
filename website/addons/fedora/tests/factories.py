# -*- coding: utf-8 -*-
"""Factory boy factories for the Fedora addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.fedora.model import (
    AddonFedoraUserSettings,
    AddonFedoraNodeSettings
)

class FedoraAccountFactory(ExternalAccountFactory):
    provider = 'fedora'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = Sequence(lambda n: 'https://localhost/{0}/fedora'.format(n))
    oauth_secret = Sequence(lambda n: 'https://localhost/{0}/fedora'.format(n))
    display_name = 'catname'
    oauth_key = 'meoword'


class FedoraUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonFedoraUserSettings

    owner = SubFactory(UserFactory)


class FedoraNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonFedoraNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(FedoraUserSettingsFactory)
    folder_id = '/Documents/'
