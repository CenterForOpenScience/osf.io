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

        assert_in('email_contact', attributes)
        assert_in('email_support', attributes)
        assert_in('social_facebook', attributes)
        assert_in('social_instagram', attributes)
        assert_in('social_twitter', attributes)

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
