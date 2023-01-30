# -*- coding: utf-8 -*-
import factory

from osf_tests.factories import ExternalAccountFactory


class NextcloudInstitutionsFactory(ExternalAccountFactory):
    provider = 'nextcloudinstitutions'
    provider_id = factory.Sequence(lambda n: 'id:{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))


class NextcloudInstitutionsAccountFactory:
    def __init__(self):
        self.account = NextcloudInstitutionsFactory()


class NextcloudInstitutionsNodeSettingsFactory:
    def __init__(self):
        self.provider = NextcloudInstitutionsAccountFactory()
