# -*- coding: utf-8 -*-
"""Factory boy factories for the Fedora addon."""
from factory import SubFactory, Sequence
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.fedora.models import UserSettings, NodeSettings


class FedoraAccountFactory(ExternalAccountFactory):
    provider = 'fedora'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = Sequence(lambda n: 'https://localhost/{0}/fedora'.format(n))
    oauth_secret = Sequence(lambda n: 'https://localhost/{0}/fedora'.format(n))
    display_name = 'catname'
    oauth_key = 'meoword'


class FedoraUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = SubFactory(UserFactory)


class FedoraNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(FedoraUserSettingsFactory)
    folder_id = '/Documents/'
