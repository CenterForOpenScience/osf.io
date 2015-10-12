# -*- coding: utf-8 -*-
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory)


class TestRegistrationList(ApiTestCase):

    def setUp(self):
        super(TestRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)
        self.project.save()
        self.url = '/{}registrations/'.format(API_BASE)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_project.save()

        self.user_two = AuthUserFactory()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['registration'], True)
        url = res.json['data'][0]['relationships']['branched_from']['links']['related']['href']
        assert_equal(urlparse(url).path, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_return_registrations_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        print res
        print[self.project._id, self.registration_project._id, self.public_project._id, self.public_registration_project._id, self.user_two]
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['registration'], True)
        assert_equal(res.json['data'][1]['attributes']['registration'], True)

        branched_from_one = urlparse(res.json['data'][0]['relationships']['branched_from']['links']['related']['href']).path
        branched_from_two = urlparse(res.json['data'][1]['relationships']['branched_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_items_equal([branched_from_one, branched_from_two],
                           ['/{}nodes/{}/'.format(API_BASE, self.public_project._id),
                            '/{}nodes/{}/'.format(API_BASE, self.project._id)])

    def test_return_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['registration'], True)
        branched_from = urlparse(res.json['data'][0]['relationships']['branched_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_equal(branched_from, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

