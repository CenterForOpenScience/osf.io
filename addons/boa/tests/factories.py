from factory import DjangoModelFactory, Sequence, SubFactory

from addons.boa.models import UserSettings, NodeSettings
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory


class BoaAccountFactory(ExternalAccountFactory):

    provider = 'boa'
    provider_name = 'Fake Boa Provider'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = Sequence(lambda n: 'https://localhost:9999/{0}/boa'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
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
