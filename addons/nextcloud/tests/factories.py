# -*- coding: utf-8 -*-
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.nextcloud.models import UserSettings, NodeSettings, NextcloudFile


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


class NextcloudFactory(ExternalAccountFactory):
    provider = 'nextcloud'
    provider_id = factory.Sequence(lambda n: 'id:{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))


class NodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    external_account = factory.SubFactory(NextcloudFactory)
    owner = factory.SubFactory(ProjectFactory)


class NextcloudFileFactory(DjangoModelFactory):
    class Meta:
        model = NextcloudFile

    provider = 'nextcloud'
    path = 'test.txt'
    target = factory.SubFactory(ProjectFactory)
