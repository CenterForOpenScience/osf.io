from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory
from osf_tests.factories import ExternalAccountFactory, UserFactory, ProjectFactory

from addons.gitlab.models import NodeSettings, UserSettings


class GitLabAccountFactory(ExternalAccountFactory):
    provider = 'gitlab'
    provider_id = Sequence(lambda n: f'id-{n}')
    oauth_key = Sequence(lambda n: f'key-{n}')
    display_name = 'abc'


class GitLabUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = SubFactory(UserFactory)


class GitLabNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GitLabUserSettingsFactory)
