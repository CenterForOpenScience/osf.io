# -*- coding: utf-8 -*-
import functools

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from api.preprint_providers.serializers import PreprintProviderSerializer
from osf_tests.factories import (
    EmailFactory,
    PreprintProviderFactory,
    ExternalLinkFactory,
    SocialAccountFactory
)
from tests.base import DbTestCase
from tests.utils import make_drf_request_with_version


class TestPreprintProviderSerializer(DbTestCase):

    def setUp(self):
        super(TestPreprintProviderSerializer, self).setUp()
        self.preprint_provider = PreprintProviderFactory()

        self.email = EmailFactory()
        self.social_account = SocialAccountFactory()
        self.provider_link = ExternalLinkFactory()

        self.preprint_provider.emails.add(self.email)
        self.preprint_provider.social_accounts.add(self.social_account)
        self.preprint_provider.links.add(self.provider_link)

    def test_preprint_provider_serialization_v2(self):
        req = make_drf_request_with_version(version='2.0')
        result = PreprintProviderSerializer(self.preprint_provider, context={'request': req}).data

        data = result['data']
        attributes = data['attributes']

        assert_equal(data['id'], self.preprint_provider._id)
        assert_equal(data['type'], 'preprint_providers')

        assert_in('email_contact', attributes)
        assert_in('email_support', attributes)
        assert_in('social_facebook', attributes)
        assert_in('social_instagram', attributes)
        assert_in('social_twitter', attributes)

        # The assertions below are to ensure we don't accidentally remove information from the API
        # if the Email/Social/Link models change since these models are serialized using django's ModelSerializer

        assert_equal(attributes['emails'][0]['email'], self.email.email)
        assert_equal(attributes['emails'][0]['email_type'], self.email.email_type)

        assert_equal(attributes['preprint_provider_links'][0]['url'], self.provider_link.url)
        assert_equal(attributes['preprint_provider_links'][0]['linked_text'], self.provider_link.linked_text)
        assert_equal(attributes['preprint_provider_links'][0]['description'], self.provider_link.description)

        assert_equal(attributes['social_accounts'][0]['username'], self.social_account.username)
        assert_equal(attributes['social_accounts'][0]['network']['name'], self.social_account.network.name)
        assert_equal(attributes['social_accounts'][0]['network']['base_url'], self.social_account.network.base_url)

    def test_preprint_provider_serialization_v24(self):
        req = make_drf_request_with_version(version='2.4')
        result = PreprintProviderSerializer(self.preprint_provider, context={'request': req}).data

        data = result['data']
        attributes = data['attributes']

        assert_equal(data['id'], self.preprint_provider._id)
        assert_equal(data['type'], 'preprint_providers')

        assert_not_in('email_contact', attributes)
        assert_not_in('email_support', attributes)
        assert_not_in('social_facebook', attributes)
        assert_not_in('social_instagram', attributes)
        assert_not_in('social_twitter', attributes)
