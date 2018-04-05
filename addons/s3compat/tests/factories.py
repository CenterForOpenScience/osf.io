# -*- coding: utf-8 -*-
"""Factories for the S3 Compatible Storage addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.s3compat.models import (
    UserSettings,
    NodeSettings
)

class S3CompatAccountFactory(ExternalAccountFactory):
    provider = 's3compat'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'secret-{0}'.format(n))
    display_name = 'S3 Compatible Storage Fake User'


class S3CompatUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class S3CompatNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(S3CompatUserSettingsFactory)
