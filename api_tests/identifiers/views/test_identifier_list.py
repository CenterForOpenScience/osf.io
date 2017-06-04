# -*- coding: utf-8 -*-
import urlparse
from modularodm import Q
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from website.identifiers.model import Identifier

from tests.base import ApiTestCase
from tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    IdentifierFactory,
    NodeFactory,
)


class TestRegistrationIdentifierList(ApiTestCase):

    def setUp(self):
        super(TestRegistrationIdentifierList, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.identifier = IdentifierFactory(referent=self.registration)
        self.url = '/{}registrations/{}/identifiers/'.format(API_BASE, self.registration._id)

        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

        self.all_identifiers = Identifier.find()

    def tearDown(self):
        super(TestRegistrationIdentifierList, self).tearDown()
        Identifier.remove()

    def test_identifier_list_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_identifier_list_returns_correct_number(self):
        total = self.res.json['links']['meta']['total']
        assert_equal(total, self.all_identifiers.count())

    def test_identifier_list_returns_correct_referent(self):
        paths = [
            urlparse.urlparse(
                item['relationships']['referent']['links']['related']['href']
            ).path for item in self.data
        ]
        assert_in('/{}registrations/{}/'.format(API_BASE, self.registration._id), paths)

    def test_identifier_list_returns_correct_categories(self):
        categories = [identifier.category for identifier in self.all_identifiers]
        categories_in_response = [identifier['attributes']['category'] for identifier in self.data]

        assert_items_equal(categories_in_response, categories)

    def test_identifier_list_returns_correct_values(self):
        values = [identifier.value for identifier in self.all_identifiers]
        values_in_response = [identifier['attributes']['value'] for identifier in self.data]

        assert_items_equal(values_in_response, values)

    def test_identifier_filter_by_category(self):
        IdentifierFactory(referent=self.registration, category='nopeid')
        identifiers_for_registration = Identifier.find(Q('referent', 'eq', self.registration))
        assert_equal(len(identifiers_for_registration), 2)
        assert_items_equal(
            [identifier.category for identifier in identifiers_for_registration],
            ['carpid', 'nopeid']
        )

        filter_url = self.url + '?filter[category]=carpid'
        new_res = self.app.get(filter_url)

        carpid_total = len(Identifier.find(Q('category', 'eq', 'carpid')))

        total = new_res.json['links']['meta']['total']
        assert_equal(total, carpid_total)

    def test_node_identifier_not_returned_from_registration_endpoint(self):
        self.node = NodeFactory(creator=self.user, is_public=True)
        self.node_identifier = IdentifierFactory(referent=self.node)
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(self.identifier._id, data[0]['id'])
        assert_not_equal(self.node_identifier._id, data[0]['id'])

    def test_node_not_allowed_from_registrations_endpoint(self):
        self.node = NodeFactory(creator=self.user, is_public=True)
        self.node_identifier = IdentifierFactory(referent=self.node)
        url = '/{}registrations/{}/identifiers/'.format(API_BASE, self.node._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)


class TestNodeIdentifierList(ApiTestCase):

    def setUp(self):
        super(TestNodeIdentifierList, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.node = NodeFactory(creator=self.user, is_public=True)
        self.identifier = IdentifierFactory(referent=self.node)
        self.url = '/{}nodes/{}/identifiers/'.format(API_BASE, self.node._id)

        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

        self.all_identifiers = Identifier.find()

    def tearDown(self):
        super(TestNodeIdentifierList, self).tearDown()
        Identifier.remove()

    def test_identifier_list_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_identifier_list_returns_correct_number(self):
        total = self.res.json['links']['meta']['total']
        assert_equal(total, self.all_identifiers.count())

    def test_identifier_list_returns_correct_referent(self):
        paths = [
            urlparse.urlparse(
                item['relationships']['referent']['links']['related']['href']
            ).path for item in self.data
        ]
        assert_in('/{}nodes/{}/'.format(API_BASE, self.node._id), paths)

    def test_identifier_list_returns_correct_categories(self):
        categories = [identifier.category for identifier in self.all_identifiers]
        categories_in_response = [identifier['attributes']['category'] for identifier in self.data]

        assert_items_equal(categories_in_response, categories)

    def test_identifier_list_returns_correct_values(self):
        values = [identifier.value for identifier in self.all_identifiers]
        values_in_response = [identifier['attributes']['value'] for identifier in self.data]

        assert_items_equal(values_in_response, values)

    def test_identifier_filter_by_category(self):
        IdentifierFactory(referent=self.node, category='nopeid')
        identifiers_for_node = Identifier.find(Q('referent', 'eq', self.node))
        assert_equal(len(identifiers_for_node), 2)
        assert_items_equal(
            [identifier.category for identifier in identifiers_for_node],
            ['carpid', 'nopeid']
        )

        filter_url = self.url + '?filter[category]=carpid'
        new_res = self.app.get(filter_url)

        carpid_total = len(Identifier.find(Q('category', 'eq', 'carpid')))

        total = new_res.json['links']['meta']['total']
        assert_equal(total, carpid_total)

    def test_registration_identifier_not_returned_from_registration_endpoint(self):
        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.registration_identifier = IdentifierFactory(referent=self.registration)
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(self.identifier._id, data[0]['id'])
        assert_not_equal(self.registration_identifier._id, data[0]['id'])

    def test_registration_not_allowed_from_nodes_endpoint(self):
        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.registration_identifier = IdentifierFactory(referent=self.registration)
        url = '/{}nodes/{}/identifiers/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)
