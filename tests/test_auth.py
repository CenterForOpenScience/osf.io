#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
import mock

from flask import Flask
from webtest_plus import TestApp

import framework.auth as auth
from tests.base import DbTestCase
from tests.factories import UserFactory

from framework import Q
from framework.auth.model import User
from framework.auth.decorators import must_be_logged_in, Auth

class TestAuthUtils(DbTestCase):

    def test_register(self):
        auth.register('rosie@franklin.com', 'gattaca', fullname="Rosie Franklin")
        user = User.find_one(Q('username', 'eq', 'rosie@franklin.com'))
        # The password should be set
        assert_true(user.check_password('gattaca'))
        assert_equal(user.fullname, "Rosie Franklin")
        assert_equal(user.username, 'rosie@franklin.com')
        assert_in("rosie@franklin.com", user.emails)

    def test_get_user_by_id(self):
        user = UserFactory()
        assert_equal(auth.get_user(id=user._id), user)

    def test_get_user_by_username(self):
        user = UserFactory()
        assert_equal(auth.get_user(username=user.username), user)

    def test_get_user_with_wrong_password_returns_false(self):
        user = UserFactory.build()
        user.set_password('killerqueen')
        assert_false(auth.get_user(username=user.username,
            password='wrong'))


class TestAuthObject(DbTestCase):

    def test_from_kwargs(self):
        user = UserFactory()
        request_args = {'key': 'mykey'}
        kwargs = {'user': user, 'api_key': 'myapikey', 'api_node': '123v'}
        auth = Auth.from_kwargs(request_args, kwargs)
        assert_equal(auth.user, user)
        assert_equal(auth.api_key, kwargs['api_key'])
        assert_equal(auth.private_key, request_args['key'])

    def test_logged_in(self):
        user = UserFactory()
        auth = Auth(user=user)
        assert_true(auth.logged_in)
        auth2 = Auth(user=None)
        assert_false(auth2.logged_in)


# Flask app for testing view decorators
app = Flask(__name__)

@app.route('/login/')
def login():
    return 'The login page'

@app.route('/protected/')
@must_be_logged_in
def protected(**kwargs):
    return 'open sesame'

class TestDecorators(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)

    @mock.patch('framework.auth.decorators.get_current_user')
    def test_must_be_logged_in_decorator_with_user(self, mock_get_current_user):
        user = UserFactory()
        mock_get_current_user.return_value = user
        # Make all params (except for user) truthy values so don't have to mock out
        # session (get_api_key, etc)
        res = self.app.get('/protected/', params={
            'api_key': 'blah',
            'api_node': '1234',
            'key': '12345'
        })
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.decorators.get_current_user')
    def test_must_be_logged_in_decorator_with_no_user_redirects_to_login_page(self,
        mock_get_current_user):
        mock_get_current_user.return_value = None
        res = self.app.get('/protected/', params={
            'api_key': 'blah',
            'api_node': '1234',
            'key': '12345'
        })
        assert_equal(res.status_code, 302, 'redirect request')
        res = res.follow()  # Follow the redirect
        assert_equal(res.request.path, '/login/', 'at the login page')



if __name__ == '__main__':
    unittest.main()
