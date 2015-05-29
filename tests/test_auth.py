#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # noqa; PEP8 asserts
from webtest_plus import TestApp
import mock
import datetime
import httplib as http

from flask import Flask
from werkzeug.wrappers import BaseResponse

from framework import auth
from framework.auth import cas
from framework.exceptions import HTTPError
from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import (
    UserFactory, UnregUserFactory, AuthFactory,
    ProjectFactory, NodeFactory, AuthUserFactory, PrivateLinkFactory
)

from framework.auth import User, Auth
from framework.auth.decorators import must_be_logged_in

from website.util import web_url_for
from website.project.decorators import (
    must_have_permission, must_be_contributor,
    must_have_addon, must_be_addon_authorizer,
)


class TestAuthUtils(OsfTestCase):

    def test_unreg_user_can_register(self):
        user = UnregUserFactory()

        auth.register_unconfirmed(
            username=user.username,
            password='gattaca',
            fullname='Rosie',
        )

        assert_true(user.get_confirmation_token(user.username))

    def test_get_user_by_id(self):
        user = UserFactory()
        assert_equal(User.load(user._id), user)

    def test_get_user_by_email(self):
        user = UserFactory()
        assert_equal(auth.get_user(email=user.username), user)

    def test_get_user_with_wrong_password_returns_false(self):
        user = UserFactory.build()
        user.set_password('killerqueen')
        assert_false(
            auth.get_user(email=user.username, password='wrong')
        )


class TestAuthObject(OsfTestCase):

    def test_repr(self):
        auth = AuthFactory()
        rep = repr(auth)
        assert_in(str(auth.user), rep)

    def test_factory(self):
        auth_obj = AuthFactory()
        assert_true(isinstance(auth_obj.user, auth.User))
        assert_true(auth_obj.api_key)

    def test_from_kwargs(self):
        user = UserFactory()
        request_args = {'view_only': 'mykey'}
        kwargs = {'user': user, 'api_key': 'myapikey', 'api_node': '123v'}
        auth_obj = Auth.from_kwargs(request_args, kwargs)
        assert_equal(auth_obj.user, user)
        assert_equal(auth_obj.api_key, kwargs['api_key'])
        assert_equal(auth_obj.private_key, request_args['view_only'])

    def test_logged_in(self):
        user = UserFactory()
        auth_obj = Auth(user=user)
        assert_true(auth_obj.logged_in)
        auth2 = Auth(user=None)
        assert_false(auth2.logged_in)


class TestPrivateLink(OsfTestCase):

    def setUp(self):
        super(TestPrivateLink, self).setUp()
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

    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_has_private_link_key(self, mock_from_kwargs):
        mock_from_kwargs.return_value = Auth(user=None)
        res = self.app.get('/project/{0}'.format(self.project._primary_key),
            {'view_only': self.link.key})
        res = res.follow()
        assert_equal(res.status_code, 200)
        assert_equal(res.body, 'success')

    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_does_not_have_key(self, mock_from_kwargs):
        mock_from_kwargs.return_value = Auth(user=None)
        res = self.app.get('/project/{0}'.format(self.project._primary_key),
            {'key': None})
        assert_is_redirect(res)


# Flask app for testing view decorators
decoratorapp = Flask('decorators')


@must_be_contributor
def view_that_needs_contributor(**kwargs):
    return kwargs.get('node') or kwargs.get('parent')


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
        # redirects to login url
        redirect_url = res.headers['Location']
        login_url = cas.get_login_url(service_url='http://localhost/')
        assert_equal(redirect_url, login_url)

    def test_must_be_contributor_parent_admin(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        res = view_that_needs_contributor(
            pid=self.project._id,
            nid=node._id,
            user=self.project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_write(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        self.project.set_permissions(self.project.creator, ['read', 'write'])
        self.project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor(
                pid=self.project._id,
                nid=node._id,
                user=self.project.creator,
            )
        assert_equal(exc_info.exception.code, 403)


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
        login_url = cas.get_login_url(service_url='http://localhost/')
        assert_in(login_url, resp.headers.get('location'))

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_true(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        project.add_permission(project.creator, 'dance')
        mock_from_kwargs.return_value = Auth(user=project.creator)
        mock_to_nodes.return_value = (None, project)
        thriller(node=project)

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_false(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        mock_from_kwargs.return_value = Auth(user=project.creator)
        mock_to_nodes.return_value = (None, project)
        with assert_raises(HTTPError) as ctx:
            thriller(node=project)
        assert_equal(ctx.exception.code, http.FORBIDDEN)

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_not_logged_in(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        mock_from_kwargs.return_value = Auth()
        mock_to_nodes.return_value = (None, project)
        with assert_raises(HTTPError) as ctx:
            thriller(node=project)
        assert_equal(ctx.exception.code, http.UNAUTHORIZED)


def needs_addon_view(**kwargs):
    return 'openaddon'


class TestMustHaveAddonDecorator(AuthAppTestCase):

    def setUp(self):
        super(TestMustHaveAddonDecorator, self).setUp()
        self.project = ProjectFactory()

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    def test_must_have_addon_node_true(self, mock_kwargs_to_nodes):
        mock_kwargs_to_nodes.return_value = (None, self.project)
        self.project.add_addon('github', auth=None)
        decorated = must_have_addon('github', 'node')(needs_addon_view)
        res = decorated()
        assert_equal(res, 'openaddon')

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    def test_must_have_addon_node_false(self, mock_kwargs_to_nodes):
        mock_kwargs_to_nodes.return_value = (None, self.project)
        self.project.delete_addon('github', auth=None)
        decorated = must_have_addon('github', 'node')(needs_addon_view)
        with assert_raises(HTTPError):
            decorated()

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_addon_user_true(self, mock_current_user):
        mock_current_user.return_value = Auth(self.project.creator)
        self.project.creator.add_addon('github')
        decorated = must_have_addon('github', 'user')(needs_addon_view)
        res = decorated()
        assert_equal(res, 'openaddon')

    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_addon_user_false(self, mock_current_user):
        mock_current_user.return_value = Auth(self.project.creator)
        self.project.creator.delete_addon('github')
        decorated = must_have_addon('github', 'user')(needs_addon_view)
        with assert_raises(HTTPError):
            decorated()


class TestMustBeAddonAuthorizerDecorator(AuthAppTestCase):

    def setUp(self):
        super(TestMustBeAddonAuthorizerDecorator, self).setUp()
        self.project = ProjectFactory()
        self.decorated = must_be_addon_authorizer('github')(needs_addon_view)

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_be_authorizer_true(self, mock_get_current_user, mock_kwargs_to_nodes):

        # Mock
        mock_get_current_user.return_value = Auth(self.project.creator)
        mock_kwargs_to_nodes.return_value = (None, self.project)

        # Setup
        self.project.add_addon('github', auth=None)
        node_settings = self.project.get_addon('github')
        self.project.creator.add_addon('github')
        user_settings = self.project.creator.get_addon('github')
        node_settings.user_settings = user_settings

        # Test
        res = self.decorated()
        assert_equal(res, 'openaddon')

    def test_must_be_authorizer_false(self):

        # Setup
        self.project.add_addon('github', auth=None)
        node_settings = self.project.get_addon('github')
        user2 = UserFactory()
        user2.add_addon('github')
        user_settings = user2.get_addon('github')
        node_settings.user_settings = user_settings

        # Test
        with assert_raises(HTTPError):
            self.decorated()

    def test_must_be_authorizer_no_user_settings(self):
        self.project.add_addon('github', auth=None)
        with assert_raises(HTTPError):
            self.decorated()

    def test_must_be_authorizer_no_node_settings(self):
        with assert_raises(HTTPError):
            self.decorated()

class TestBasicAuth(OsfTestCase):

    def test_basic_auth_returns_403(self):
        url = web_url_for('dashboard')
        ret = self.app.get(url, auth=('test', 'test'), expect_errors=True)
        assert_equal(ret.status_code, 403)


if __name__ == '__main__':
    unittest.main()
