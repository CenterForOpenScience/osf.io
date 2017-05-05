# -*- coding: utf-8 -*-
"""Factories for the AzureBlobStorage addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.azureblobstorage.models import (
    UserSettings,
    NodeSettings
)

class AzureBlobStorageAccountFactory(ExternalAccountFactory):
    provider = 'azureblobstorage'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n:'secret-{0}'.format(n))
    display_name = 'Azure Blob Storage Fake User'


class AzureBlobStorageUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class AzureBlobStorageNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model =  NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(AzureBlobStorageUserSettingsFactory)
