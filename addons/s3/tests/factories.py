"""Factories for the S3 addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.s3.models import (
    UserSettings,
    NodeSettings
)

class S3AccountFactory(ExternalAccountFactory):
    provider = 's3'
    provider_id = factory.Sequence(lambda n: f'id-{n}')
    oauth_key = factory.Sequence(lambda n: f'key-{n}')
    oauth_secret = factory.Sequence(lambda n: f'secret-{n}')
    display_name = 'S3 Fake User'


class S3UserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class S3NodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(S3UserSettingsFactory)
