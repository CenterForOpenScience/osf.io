# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import urlparse

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
        categories = [identifier.value for identifier in self.all_identifiers]
        categories_in_response = [identifier['attributes']['identifier']['self'] for identifier in self.data]

        assert_items_equal(categories_in_response, categories)
