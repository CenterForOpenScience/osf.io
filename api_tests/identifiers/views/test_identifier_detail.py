# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import urlparse
from api.base.settings.defaults import API_BASE
from website.identifiers.model import Identifier

from tests.base import ApiTestCase
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    IdentifierFactory,
    NodeFactory,
)


class TestIdentifierDetail(ApiTestCase):

    def setUp(self):
        super(TestIdentifierDetail, self).setUp()
        self.user = AuthUserFactory()

        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.registration_identifier = IdentifierFactory(referent=self.registration)
        self.registration_url = '/{}identifiers/{}/'.format(API_BASE, self.registration_identifier._id)

        self.node = NodeFactory(creator=self.user, is_public=True)
        self.node_identifier = IdentifierFactory(referent=self.node)
        self.node_url = '/{}identifiers/{}/'.format(API_BASE, self.node_identifier._id)

        self.registration_res = self.app.get(self.registration_url)
        self.registration_data = self.registration_res.json['data']

        self.node_res = self.app.get(self.node_url)
        self.node_data = self.node_res.json['data']

    def test_identifier_detail_success_registration(self):
        assert_equal(self.registration_res.status_code, 200)
        assert_equal(self.registration_res.content_type, 'application/vnd.api+json')

    def test_identifier_detail_success_node(self):
        assert_equal(self.node_res.status_code, 200)
        assert_equal(self.node_res.content_type, 'application/vnd.api+json')

    def test_identifier_detail_returns_correct_referent_registration(self):
        path = urlparse.urlparse(self.registration_data['relationships']['referent']['links']['related']['href']).path
        assert_equal('/{}registrations/{}/'.format(API_BASE, self.registration._id), path)

    def test_identifier_detail_returns_correct_referent_node(self):
        path = urlparse.urlparse(self.node_data['relationships']['referent']['links']['related']['href']).path
        assert_equal('/{}nodes/{}/'.format(API_BASE, self.node._id), path)

    def test_identifier_detail_returns_correct_category_registration(self):
        assert_equal(self.registration_data['attributes']['category'], self.registration_identifier.category)

    def test_identifier_detail_returns_correct_category_node(self):
        assert_equal(self.node_data['attributes']['category'], self.node_identifier.category)

    def test_identifier_detail_returns_correct_value_registration(self):
        assert_equal(self.registration_data['attributes']['value'], self.registration_identifier.value)

    def test_identifier_detail_returns_correct_value_node(self):
        assert_equal(self.node_data['attributes']['value'], self.node_identifier.value)
