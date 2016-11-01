# -*- coding: utf-8 -*-
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.owncloud.models import UserSettings, NodeSettings


class OwnCloudAccountFactory(ExternalAccountFactory):
    provider = 'owncloud'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = factory.Sequence(lambda n: 'https://localhost/{0}/owncloud'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'https://localhost/{0}/owncloud'.format(n))
    display_name = 'catname'
    oauth_key = 'meoword'


class OwnCloudUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class OwnCloudNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(OwnCloudUserSettingsFactory)
    folder_id = '/Documents/'
