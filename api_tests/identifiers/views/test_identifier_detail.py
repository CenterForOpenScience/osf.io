# -*- coding: utf-8 -*-
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    IdentifierFactory
)

class TestIdentifierDetail(ApiTestCase):
    def setUp(self):
        super(TestIdentifierDetail, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.public_registration = RegistrationFactory(creator=self.user, is_public=True)
        self.private_registration = RegistrationFactory(creator=self.user)

        self.identifier = IdentifierFactory(referent=self.public_registration)
