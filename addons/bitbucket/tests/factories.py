from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory
from osf_tests.factories import ExternalAccountFactory, ProjectFactory, UserFactory

from addons.bitbucket.models import NodeSettings, UserSettings


class BitbucketAccountFactory(ExternalAccountFactory):
    provider = 'bitbucket'
    provider_id = Sequence(lambda n: f'id-{n}')
    oauth_key = Sequence(lambda n: f'key-{n}')
    display_name = 'abc'


class BitbucketUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = SubFactory(UserFactory)


class BitbucketNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BitbucketUserSettingsFactory)
