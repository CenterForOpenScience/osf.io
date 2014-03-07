#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
import mock
import datetime

from flask import Flask
from werkzeug.wrappers import BaseResponse
from webtest_plus import TestApp
import httplib as http

from framework.exceptions import HTTPError
import framework.auth as auth
from tests.base import DbTestCase
from tests.factories import UserFactory, UnregUserFactory, AuthFactory, ProjectFactory

from framework import Q
from framework import app
from framework.auth.model import User
from framework.auth.decorators import must_be_logged_in, Auth

from website.project.decorators import must_have_permission

class TestAuthUtils(DbTestCase):

    def test_register(self):
        auth.register('rosie@franklin.com', 'gattaca', fullname="Rosie Franklin")
        user = User.find_one(Q('username', 'eq', 'rosie@franklin.com'))
        # The password should be set
        assert_true(user.check_password('gattaca'))
        assert_equal(user.fullname, "Rosie Franklin")
        assert_equal(user.username, 'rosie@franklin.com')
        assert_in("rosie@franklin.com", user.emails)

    def test_unreg_user_can_register(self):
        user = UnregUserFactory()

        auth.register_unconfirmed(username=user.username,
            password='gattaca', fullname='Rosie')

        assert_true(user.get_confirmation_token(user.username))

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

    def test_login_success_authenticates_user(self):
        user = UserFactory.build(date_last_login=datetime.datetime.utcnow())
        user.set_password('killerqueen')
        user.save()
        # need request context because login returns a rsponse
        with app.test_request_context():
            res = auth.login(user.username, 'killerqueen')
            assert_true(isinstance(res, BaseResponse))
            assert_equal(res.status_code, 302)

    def test_login_unregistered_user(self):
        user = UnregUserFactory()
        user.set_password('killerqueen')
        user.save()
        with assert_raises(auth.LoginNotAllowedError):
            # password is correct, but user is unregistered
            auth.login(user.username, 'killerqueen')

    def test_login_with_incorrect_password_returns_false(self):
        user = UserFactory.build()
        user.set_password('rhapsody')
        user.save()
        with assert_raises(auth.PasswordIncorrectError):
            auth.login(user.username, 'wrongpassword')


class TestAuthObject(DbTestCase):

    def test_factory(self):
        auth_obj = AuthFactory()
        assert_true(isinstance(auth_obj.user, auth.model.User))
        assert_true(auth_obj.api_key)

    def test_from_kwargs(self):
        user = UserFactory()
        request_args = {'key': 'mykey'}
        kwargs = {'user': user, 'api_key': 'myapikey', 'api_node': '123v'}
        auth_obj = Auth.from_kwargs(request_args, kwargs)
        assert_equal(auth_obj.user, user)
        assert_equal(auth_obj.api_key, kwargs['api_key'])
        assert_equal(auth_obj.private_key, request_args['key'])

    def test_logged_in(self):
        user = UserFactory()
        auth_obj = Auth(user=user)
        assert_true(auth_obj.logged_in)
        auth2 = Auth(user=None)
        assert_false(auth2.logged_in)


# Flask app for testing view decorators
app = Flask(__name__)

@must_be_logged_in
def protected(**kwargs):
    return 'open sesame'

@must_have_permission('dance')
def thriller(**kwargs):
    return 'chiller'

class TestDecorators(DbTestCase):

    def setUp(self):
        self.ctx = app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_be_logged_in_decorator_with_user(self, mock_from_kwargs):
        user = UserFactory()
        mock_from_kwargs.return_value = Auth(user=user)
        protected()

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_be_logged_in_decorator_with_no_user(self, mock_from_kwargs):
        mock_from_kwargs.return_value = Auth()
        resp = protected()
        assert_true(isinstance(resp, BaseResponse))
        assert_in('/login/', resp.headers.get('location'))

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_true(self, mock_from_kwargs):
        project = ProjectFactory()
        project.add_permission(project.creator, 'dance')
        mock_from_kwargs.return_value = Auth(user=project.creator)
        thriller(node=project)

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_false(self, mock_from_kwargs):
        project = ProjectFactory()
        mock_from_kwargs.return_value = Auth(user=project.creator)
        with assert_raises(HTTPError) as ctx:
            thriller(node=project)
        assert_equal(ctx.exception.code, http.FORBIDDEN)

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_not_logged_in(self, mock_from_kwargs):
        project = ProjectFactory()
        mock_from_kwargs.return_value = Auth()
        with assert_raises(HTTPError) as ctx:
            thriller(node=project)
        assert_equal(ctx.exception.code, http.UNAUTHORIZED)


if __name__ == '__main__':
    unittest.main()
