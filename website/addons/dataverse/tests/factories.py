# -*- coding: utf-8 -*-
"""Factory boy factories for the Dataverse addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.dataverse.model import (
    AddonDataverseUserSettings,
    AddonDataverseNodeSettings
)

class DataverseAccountFactory(ExternalAccountFactory):
    provider = 'dataverse'
    provider_name='Dataverse'

    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    display_name='foo.bar.baz'
    oauth_secret='doremi-abc-123'


class DataverseUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonDataverseUserSettings

    owner = SubFactory(UserFactory)


class DataverseNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AddonDataverseNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(DataverseUserSettingsFactory)
