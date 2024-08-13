from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory

from addons.boa.models import UserSettings, NodeSettings
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

BOA_HOST = 'http://localhost:9999/boa/?q=boa/api'
BOA_USERNAME = 'fake-boa-username'
BOA_PASSWORD = 'fake-boa-password'


class BoaAccountFactory(ExternalAccountFactory):

    provider = 'boa'
    provider_name = 'Fake Boa Provider'
    provider_id = Sequence(lambda n: f'{BOA_HOST}:{BOA_USERNAME}-{n}')
    profile_url = Sequence(lambda n: f'http://localhost:9999/{n}/boa')
    oauth_secret = Sequence(lambda n: f'secret-{n}')
    oauth_key = BOA_PASSWORD
    display_name = 'Fake Boa'


class BoaUserSettingsFactory(DjangoModelFactory):

    class Meta:
        model = UserSettings

    owner = SubFactory(UserFactory)


class BoaNodeSettingsFactory(DjangoModelFactory):

    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BoaUserSettingsFactory)
