# -*- coding: utf-8 -*-
"""Factories for the WEKO addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.weko.models import (
    UserSettings,
    NodeSettings
)

class WEKOAccountFactory(ExternalAccountFactory):
    provider = 'weko'
    provider_id = factory.Sequence(lambda n: 'repo-{0}:id-{0}'.format(n, n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n:'secret-{0}'.format(n))
    display_name = 'WEKO Fake User'


class WEKOUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class WEKONodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model =  NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(WEKOUserSettingsFactory)
