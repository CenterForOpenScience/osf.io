# -*- coding: utf-8 -*-
import urlparse
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory

from api.base.settings.defaults import API_BASE


class TestUsers(ApiTestCase):

    def setUp(self):
        super(TestUsers, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()

    def tearDown(self):
        super(TestUsers, self).tearDown()

    def test_returns_200(self):
        res = self.app.get('/{}users/'.format(API_BASE))
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_find_user_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/{}users/?filter[full_name]=fred".format(API_BASE)

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/{}users/?filter[full_name]=my".format(API_BASE)
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/{}users/?filter[full_name]=NotMyMom".format(API_BASE)
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_not_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_users_list_takes_profile_image_size_param(self):
        size = 42
        url = "/{}users/?profile_image_size={}".format(API_BASE, size)
        res = self.app.get(url)
        user_json = res.json['data']
        for user in user_json:
            profile_image_url = user['links']['profile_image']
            query_dict = urlparse.parse_qs(urlparse.urlparse(profile_image_url).query)
            assert_equal(int(query_dict.get('s')[0]), size)

