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
    IdentifierFactory
)


class TestIdentifierList(ApiTestCase):
    def setUp(self):
        super(TestIdentifierList, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.identifier = IdentifierFactory(referent=self.registration)
        self.url = '/{}nodes/{}/identifiers/'.format(API_BASE, self.registration._id)

        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

        self.all_identifiers = Identifier.find()

    def tearDown(self):
        super(TestIdentifierList, self).tearDown()
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
