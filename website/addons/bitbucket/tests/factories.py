# -*- coding: utf-8 -*-

from factory import Sequence, SubFactory
from tests.factories import ExternalAccountFactory, ModularOdmFactory, ProjectFactory, UserFactory

from website.addons.bitbucket.model import BitbucketNodeSettings, BitbucketUserSettings


class BitbucketAccountFactory(ExternalAccountFactory):
    provider = 'bitbucket'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    display_name = 'abc'


class BitbucketUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = BitbucketUserSettings

    owner = SubFactory(UserFactory)


class BitbucketNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = BitbucketNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BitbucketUserSettingsFactory)
