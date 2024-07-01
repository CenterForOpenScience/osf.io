"""Factory boy factories for the Dataverse addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.dataverse.models import UserSettings, NodeSettings

class DataverseAccountFactory(ExternalAccountFactory):
    provider = 'dataverse'
    provider_name = 'Dataverse'

    provider_id = factory.Sequence(lambda n: f'id-{n}')
    oauth_key = factory.Sequence(lambda n: f'key-{n}')
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
