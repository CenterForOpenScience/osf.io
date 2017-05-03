# -*- coding: utf-8 -*-
"""Factories for the Swift addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.swift.models import (
    UserSettings,
    NodeSettings
)

class SwiftAccountFactory(ExternalAccountFactory):
    provider = 'swift'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = factory.Sequence(lambda n: 'auth-url-{0}\ttenant-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n:'secret-{0}'.format(n))
    display_name = 'Swift Fake User'


class SwiftUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class SwiftNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model =  NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(SwiftUserSettingsFactory)
