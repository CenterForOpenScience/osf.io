# -*- coding: utf-8 -*-
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.nextcloud.models import UserSettings, NodeSettings


class NextcloudAccountFactory(ExternalAccountFactory):
    provider = 'nextcloud'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    profile_url = factory.Sequence(lambda n: 'https://localhost/{0}/nextcloud'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'https://localhost/{0}/nextcloud'.format(n))
    display_name = 'catname'
    oauth_key = 'meoword'


class NextcloudUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class NextcloudNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(NextcloudUserSettingsFactory)
    folder_id = '/Documents/'
