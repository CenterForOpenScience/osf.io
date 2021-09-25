# -*- coding: utf-8 -*-
"""Factories for the My MinIO addon."""
import factory
from factory.django import DjangoModelFactory

from addons.onedrivebusiness import SHORT_NAME
from addons.onedrivebusiness.models import (
    UserSettings,
    NodeSettings
)
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory


class OneDriveBusinessAccountFactory(ExternalAccountFactory):
    provider = SHORT_NAME
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'secret-{0}'.format(n))
    display_name = 'My MinIO Fake User'


class OneDriveBusinessUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class OneDriveBusinessNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(OneDriveBusinessUserSettingsFactory)
