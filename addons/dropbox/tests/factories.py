import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.dropbox.models import NodeSettings
from addons.dropbox.models import UserSettings


class DropboxUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)
    # access_token = factory.Sequence(lambda n: 'abcdef{0}'.format(n))


class DropboxNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    folder = 'Camera Uploads'
    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(DropboxUserSettingsFactory)
    external_account = factory.SubFactory(ExternalAccountFactory)

class DropboxAccountFactory(ExternalAccountFactory):
    provider = 'dropbox'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
