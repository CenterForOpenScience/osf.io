# -*- coding: utf-8 -*-
from nose.tools import *
import urlparse
from api.base.settings.defaults import API_BASE
from website.identifiers.model import Identifier

from tests.base import ApiTestCase
from tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    IdentifierFactory,
    NodeFactory,
)


class TestRegistrationIdentifierDetail(ApiTestCase):

    def setUp(self):
        super(TestRegistrationIdentifierDetail, self).setUp()
        self.user = AuthUserFactory()

        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.identifier = IdentifierFactory(referent=self.registration)
        self.url = '/{}identifiers/{}/'.format(API_BASE, self.identifier._id)

        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def tearDown(self):
        super(TestRegistrationIdentifierDetail, self).tearDown()
        Identifier.remove()

    def test_identifier_detail_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_identifier_detail_returns_correct_referent(self):
        path = urlparse.urlparse(self.data['relationships']['referent']['links']['related']['href']).path
        assert_equal('/{}registrations/{}/'.format(API_BASE, self.registration._id), path)

    def test_identifier_detail_returns_correct_category(self):
        assert_equal(self.data['attributes']['category'], self.identifier.category)

    def test_identifier_detail_returns_correct_value(self):
        assert_equal(self.data['attributes']['value'], self.identifier.value)


class TestNodeIdentifierDetail(ApiTestCase):

    def setUp(self):
        super(TestNodeIdentifierDetail, self).setUp()
        self.user = AuthUserFactory()

        self.node = NodeFactory(creator=self.user, is_public=True)
        self.identifier = IdentifierFactory(referent=self.node)
        self.url = '/{}identifiers/{}/'.format(API_BASE, self.identifier._id)

        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def tearDown(self):
        super(TestNodeIdentifierDetail, self).tearDown()
        Identifier.remove()

    def test_identifier_detail_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_identifier_detail_returns_correct_referent(self):
        path = urlparse.urlparse(self.data['relationships']['referent']['links']['related']['href']).path
        assert_equal('/{}nodes/{}/'.format(API_BASE, self.node._id), path)

    def test_identifier_detail_returns_correct_category(self):
        assert_equal(self.data['attributes']['category'], self.identifier.category)

    def test_identifier_detail_returns_correct_value(self):
        assert_equal(self.data['attributes']['value'], self.identifier.value)
