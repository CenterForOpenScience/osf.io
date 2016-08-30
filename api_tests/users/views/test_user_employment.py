# -*- coding: utf-8 -*-
import urlparse
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory

from api.base.settings.defaults import API_BASE


class TestUserEmployment(ApiTestCase):

    def setUp(self):
        super(TestUserEmployment, self).setUp()
        self.user_one = AuthUserFactory()
        self.employment = {
            'startYear': '2010',
            'title': 'no',
            'startMonth': 1,
            'endMonth': 1,
            'endYear': '2016',
            'ongoing': False,
            'department': 'no,one',
            'institution': 'nothing'
        }
        self.user_one.jobs=[self.employment]
        self.user_one.save()

        self.user_two = AuthUserFactory()

    def tearDown(self):
        super(TestUserEmployment, self).tearDown()

    def test_gets_200(self):
        url = "/{}users/{}/employment/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_get_new_users_education_with_info(self):
        url = "/{}users/{}/employment/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_in('links', res.json)
        assert_equal(res.json['links']['meta']['total'], 1)
        assert_equal(len(res.json['data']), 1)
        employment = res.json['data'][0]
        assert_equal(employment['institution'], self.employment['institution'])
        assert_equal(employment['department'], self.employment['department'])
        assert_equal(employment['title'], self.employment['title'])
        assert_equal(employment['start_month'], str(self.employment['startMonth']))
        assert_equal(employment['start_year'], str(self.employment['startYear']))
        assert_equal(employment['end_month'], str(self.employment['endMonth']))
        assert_equal(employment['end_year'], str(self.employment['endYear']))
        assert_equal(employment['ongoing'], self.employment['ongoing'])

    def test_get_new_users_education_without_info(self):
        url = "/{}users/{}/employment/".format(API_BASE, self.user_two._id)
        res = self.app.get(url)
        assert_in('links', res.json)
        assert_equal(res.json['links']['meta']['total'], 0)
        assert_equal(len(res.json['data']), 0)

    def test_get_new_users_has_education_relationship(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_in('employment', res.json['data']['relationships'])