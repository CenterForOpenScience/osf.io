# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
from urlparse import urlparse
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)


node_url_for = lambda n_id: '/{}nodes/{}/'.format(API_BASE, n_id)


class TestNodeRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestNodeRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project, is_public=True)
        self.project.save()
        self.private_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project, is_public=True)
        self.public_project.save()
        self.public_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['registration'], True)
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert_equal(urlparse(url).path, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))
        assert_equal(res.json['data'][0]['type'], 'registrations')

    def test_return_public_registrations_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['registration'], True)
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert_equal(urlparse(url).path, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['type'], 'registrations')

    def test_return_private_registrations_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_return_private_registrations_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['registration'], True)
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert_equal(urlparse(url).path, '/{}nodes/{}/'.format(API_BASE, self.project._id))
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['type'], 'registrations')
