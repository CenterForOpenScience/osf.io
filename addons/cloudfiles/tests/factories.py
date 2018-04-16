# -*- coding: utf-8 -*-
"""Factories for the Cloud Files addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.cloudfiles.models import (
    UserSettings,
    NodeSettings
)

class CloudFilesAccountFactory(ExternalAccountFactory):
    provider = 'cloudfiles'
    display_name = 'Cloud Files Fake User'


class CloudFilesUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class CloudFilesNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(CloudFilesUserSettingsFactory)
