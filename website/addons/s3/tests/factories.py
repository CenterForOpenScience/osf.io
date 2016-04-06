# -*- coding: utf-8 -*-
"""Factories for the S3 addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.s3.model import (
    S3UserSettings,
    S3NodeSettings
)

class S3AccountFactory(ExternalAccountFactory):
    provider = 's3'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n:'secret-{0}'.format(n))
    display_name = 'S3 Fake User'


class S3UserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = S3UserSettings

    owner = SubFactory(UserFactory)


class S3NodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model =  S3NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(S3UserSettingsFactory)
    bucket = 'mock_bucket'
