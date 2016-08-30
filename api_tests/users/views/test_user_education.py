# -*- coding: utf-8 -*-
import urlparse
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory

from api.base.settings.defaults import API_BASE


class TestUserEducation(ApiTestCase):

    def setUp(self):
        super(TestUserEducation, self).setUp()
        self.user_one = AuthUserFactory()
        self.education = {
            'startYear': '2010',
            'degree': 'no',
            'startMonth': 1,
            'endMonth': 1,
            'endYear': '2016',
            'ongoing': False,
            'department': 'no,one',
            'institution': 'nothing'
        }
        self.user_one.schools=[self.education]
        self.user_one.save()

        self.user_two = AuthUserFactory()

    def tearDown(self):
        super(TestUserEducation, self).tearDown()

    def test_gets_200(self):
        url = "/{}users/{}/education/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_get_new_users_education_with_info(self):
        url = "/{}users/{}/education/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_in('links', res.json)
        assert_equal(res.json['links']['meta']['total'], 1)
        assert_equal(len(res.json['data']), 1)
        education = res.json['data'][0]
        assert_equal(education['institution'], self.education['institution'])
        assert_equal(education['department'], self.education['department'])
        assert_equal(education['degree'], self.education['degree'])
        assert_equal(education['start_month'], str(self.education['startMonth']))
        assert_equal(education['start_year'], str(self.education['startYear']))
        assert_equal(education['end_month'], str(self.education['endMonth']))
        assert_equal(education['end_year'], str(self.education['endYear']))
        assert_equal(education['ongoing'], self.education['ongoing'])

    def test_get_new_users_education_without_info(self):
        url = "/{}users/{}/education/".format(API_BASE, self.user_two._id)
        res = self.app.get(url)
        assert_in('links', res.json)
        assert_equal(res.json['links']['meta']['total'], 0)
        assert_equal(len(res.json['data']), 0)

    def test_get_new_users_has_education_relationship(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_in('education', res.json['data']['relationships'])