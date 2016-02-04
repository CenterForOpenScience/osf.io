# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, InstitutionFactory

from api.base.settings.defaults import API_BASE

class TestUserInstititutionRelationship(ApiTestCase):

    def setUp(self):
        super(TestUserInstititutionRelationship, self).setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.url = '/{}users/{}/relationships/institutions/'.format(API_BASE, self.user._id)
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.append(self.institution1)
        self.user.affiliated_institutions.append(self.institution2)
        self.user.save()
