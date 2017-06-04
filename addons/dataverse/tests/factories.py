# -*- coding: utf-8 -*-
"""Factory boy factories for the Dataverse addon."""
import factory
from factory.django import DjangoModelFactory
from tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.dataverse.models import UserSettings, NodeSettings

class DataverseAccountFactory(ExternalAccountFactory):
    provider = 'dataverse'
    provider_name = 'Dataverse'

    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    display_name = 'foo.bar.baz'
    oauth_secret = 'doremi-abc-123'


class DataverseUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class DataverseNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(DataverseUserSettingsFactory)
