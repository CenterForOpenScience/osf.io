# -*- coding: utf-8 -*-
import functools

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from api.preprint_providers.serializers import PreprintProviderSerializer
from osf_tests.factories import PreprintProviderFactory
from tests.base import DbTestCase
from tests.utils import make_drf_request_with_version


class TestPreprintProviderSerializer(DbTestCase):

    def setUp(self):
        super(TestPreprintProviderSerializer, self).setUp()
        self.preprint_provider = PreprintProviderFactory()

    def test_preprint_provider_serialization_v2(self):
        req = make_drf_request_with_version(version='2.0')
        result = PreprintProviderSerializer(self.preprint_provider, context={'request': req}).data

        data = result['data']
        attributes = data['attributes']

        assert_equal(data['id'], self.preprint_provider._id)
        assert_equal(data['type'], 'preprint_providers')

        assert_in('banner_path', attributes)
        assert_in('logo_path', attributes)
        assert_in('header_text', attributes)
        assert_in('email_contact', attributes)
        assert_in('email_support', attributes)
        assert_in('social_facebook', attributes)
        assert_in('social_instagram', attributes)
        assert_in('social_twitter', attributes)
        assert_in('subjects_acceptable', attributes)

    def test_preprint_provider_serialization_v24(self):
        req = make_drf_request_with_version(version='2.4')
        result = PreprintProviderSerializer(self.preprint_provider, context={'request': req}).data

        data = result['data']
        attributes = data['attributes']

        assert_equal(data['id'], self.preprint_provider._id)
        assert_equal(data['type'], 'preprint_providers')

        assert_not_in('banner_path', attributes)
        assert_not_in('logo_path', attributes)
        assert_not_in('header_text', attributes)
        assert_not_in('email_contact', attributes)
        assert_not_in('social_facebook', attributes)
        assert_not_in('social_instagram', attributes)
        assert_not_in('social_twitter', attributes)

    def test_preprint_provider_serialization_v25(self):
        req = make_drf_request_with_version(version='2.5')
        result = PreprintProviderSerializer(self.preprint_provider, context={'request': req}).data

        data = result['data']
        attributes = data['attributes']

        assert_equal(data['id'], self.preprint_provider._id)
        assert_equal(data['type'], 'preprint_providers')

        assert_not_in('banner_path', attributes)
        assert_not_in('logo_path', attributes)
        assert_not_in('header_text', attributes)
        assert_not_in('email_contact', attributes)
        assert_not_in('social_facebook', attributes)
        assert_not_in('social_instagram', attributes)
        assert_not_in('social_twitter', attributes)
        assert_not_in('subjects_acceptable', attributes)

        assert_in('name', attributes)
        assert_in('description', attributes)
        assert_in('advisory_board', attributes)
        assert_in('example', attributes)
        assert_in('domain', attributes)
        assert_in('domain_redirect_enabled', attributes)
        assert_in('footer_links', attributes)
        assert_in('share_source', attributes)
        assert_in('share_publish_type', attributes)
        assert_in('email_support', attributes)
        assert_in('preprint_word', attributes)
        assert_in('allow_submissions', attributes)
        assert_in('additional_providers', attributes)
