from factory import DjangoModelFactory, Sequence, SubFactory

from addons.boa.models import UserSettings, NodeSettings
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

BOA_HOST = 'http://localhost:9999/boa/?q=boa/api'
BOA_USERNAME = 'fake-boa-username'
BOA_PASSWORD = 'fake-boa-password'


class BoaAccountFactory(ExternalAccountFactory):

    provider = 'boa'
    provider_name = 'Fake Boa Provider'
    provider_id = Sequence(lambda n: '{0}:{1}-{2}'.format(BOA_HOST, BOA_USERNAME, n))
    profile_url = Sequence(lambda n: 'http://localhost:9999/{0}/boa'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
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
