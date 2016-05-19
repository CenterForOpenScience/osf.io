# -*- coding: utf-8 -*-
from api.base.settings.defaults import API_BASE

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

        self.public_registration = RegistrationFactory(creator=self.user, is_public=True)
        self.private_registration = RegistrationFactory(creator=self.user)

        self.identifier = IdentifierFactory(referent=self.public_registration)
        self.public_url = '/{}nodes/{}/identifiers/'.format(API_BASE, self.public_registration._id)
        # self.private_url = '/{}nodes/{}/identifiers/'.format(API_BASE, self.private_registration._id)

        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def test_identifier_list_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')