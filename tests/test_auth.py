#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
import mock
import datetime
import httplib as http

from flask import Flask
from werkzeug.wrappers import BaseResponse
from webtest_plus import TestApp

from framework.exceptions import HTTPError
import framework.auth as auth
from tests.base import OsfTestCase
from tests.factories import (UserFactory, UnregUserFactory, AuthFactory,
    ProjectFactory, AuthUserFactory, PrivateLinkFactory
)

from framework import Q
from framework import app
from framework.auth.model import User
from framework.auth.decorators import must_be_logged_in, Auth

from website.project.decorators import must_have_permission, must_be_contributor


def assert_is_redirect(response, msg="Response is a redirect."):
    assert 300 <= response.status_code < 400, msg


class TestAuthUtils(OsfTestCase):

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


class TestAuthObject(OsfTestCase):

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


class TestPrivateLink(OsfTestCase):

    def setUp(self):
        self.flaskapp = Flask('testing_private_links')

        @self.flaskapp.route('/project/<pid>/')
        @must_be_contributor
        def project_get(**kwargs):
            return 'success', 200

        self.app = TestApp(self.flaskapp)

        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory()
        self.link.nodes.append(self.project)
        self.link.save()

    @mock.patch('website.project.decorators.get_api_key')
    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_has_private_link_key(self, mock_from_kwargs, mock_get_api_key):
        mock_get_api_key.return_value = 'foobar123'
        mock_from_kwargs.return_value = Auth(user=None)
        res = self.app.get('/project/{0}'.format(self.project._primary_key),
            {'key': self.link.key})
        res = res.follow()
        assert_equal(res.status_code, 200)
        assert_equal(res.body, 'success')

    @mock.patch('website.project.decorators.get_api_key')
    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_does_not_have_key(self, mock_from_kwargs, mock_get_api_key):
        mock_get_api_key.return_value = 'foobar123'
        mock_from_kwargs.return_value = Auth(user=None)
        res = self.app.get('/project/{0}'.format(self.project._primary_key),
            {'key': None})
        assert_is_redirect(res)


# Flask app for testing view decorators
decoratorapp = Flask('decorators')


@must_be_contributor
def view_that_needs_contributor(**kwargs):
    return kwargs['project'] or kwargs['node']


class AuthAppTestCase(OsfTestCase):

    def setUp(self):
        self.ctx = decoratorapp.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

class TestMustBeContributorDecorator(AuthAppTestCase):

    def setUp(self):
        super(TestMustBeContributorDecorator, self).setUp()
        self.contrib = AuthUserFactory()
        self.project = ProjectFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.project.creator))
        self.project.save()


    def test_must_be_contributor_when_user_is_contributor(self):
        result = view_that_needs_contributor(
            pid=self.project._primary_key,
            api_key=self.contrib.auth[1],
            api_node=self.project,
            user=self.contrib)
        assert_equal(result, self.project)

    def test_must_be_contributor_when_user_is_not_contributor_raises_error(self):
        non_contributor = AuthUserFactory()
        with assert_raises(HTTPError):
            view_that_needs_contributor(
                pid=self.project._primary_key,
                api_key=non_contributor.auth[1],
                api_node=non_contributor.auth[1],
                user=non_contributor
            )

    def test_must_be_contributor_no_user(self):
        res = view_that_needs_contributor(
            pid=self.project._primary_key,
            user=None,
            api_key='123',
            api_node='abc',
        )
        assert_is_redirect(res)
        redirect_url = res.headers['Location']
        assert_equal(redirect_url, '/login/?next=/')


@must_be_logged_in
def protected(**kwargs):
    return 'open sesame'


@must_have_permission('dance')
def thriller(**kwargs):
    return 'chiller'


class TestPermissionDecorators(AuthAppTestCase):

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

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_true(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        project.add_permission(project.creator, 'dance')
        mock_from_kwargs.return_value = Auth(user=project.creator)
        mock_to_nodes.return_value = (project, None)
        thriller(node=project)

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_false(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        mock_from_kwargs.return_value = Auth(user=project.creator)
        mock_to_nodes.return_value = (project, None)
        with assert_raises(HTTPError) as ctx:
            thriller(node=project)
        assert_equal(ctx.exception.code, http.FORBIDDEN)

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_not_logged_in(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        mock_from_kwargs.return_value = Auth()
        mock_to_nodes.return_value = (project, None)
        with assert_raises(HTTPError) as ctx:
            thriller(node=project)
        assert_equal(ctx.exception.code, http.UNAUTHORIZED)


if __name__ == '__main__':
    unittest.main()
