# -*- coding: utf-8 -*-
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.boa.models import UserSettings, NodeSettings


class BoaAccountFactory(ExternalAccountFactory):
    provider = 'boa'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = factory.Sequence(lambda n: 'https://localhost/{0}/boa'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'https://localhost/{0}/boa'.format(n))
    display_name = 'catname'
    oauth_key = 'meoword'


class BoaUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class BoaNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(BoaUserSettingsFactory)
    folder_id = '/Documents/'
