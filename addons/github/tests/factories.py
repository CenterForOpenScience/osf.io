import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.github.models import NodeSettings, UserSettings


class GitHubAccountFactory(ExternalAccountFactory):
    provider = 'github'
    provider_id = factory.Sequence(lambda n: f'id-{n}')
    oauth_key = factory.Sequence(lambda n: f'key-{n}')
    display_name = 'abc'


class GitHubUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class GitHubNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(GitHubUserSettingsFactory)
