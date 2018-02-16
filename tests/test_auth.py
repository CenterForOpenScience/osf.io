#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # noqa; PEP8 asserts
from webtest_plus import TestApp as WebtestApp  # py.test tries to collect `TestApp`
import mock
import urllib
import urlparse
import httplib as http

from flask import Flask
from werkzeug.wrappers import BaseResponse

from framework import auth
from framework.auth import cas
from framework.auth.utils import validate_recaptcha
from framework.exceptions import HTTPError
from tests.base import OsfTestCase, assert_is_redirect, fake
from osf_tests.factories import (
    UserFactory, UnregUserFactory, AuthFactory,
    ProjectFactory, NodeFactory, AuthUserFactory, PrivateLinkFactory
)

from framework.auth import Auth
from framework.auth.decorators import must_be_logged_in
from osf.models import OSFUser, Session
from osf.utils import permissions
from website import mails
from website import settings
from website.project.decorators import (
    must_have_permission,
    must_be_contributor,
    must_be_contributor_or_public,
    must_be_contributor_or_public_but_not_anonymized,
    must_have_addon, must_be_addon_authorizer,
)
from website.util import api_url_for

from tests.test_cas_authentication import generate_external_user_with_resp


class TestAuthUtils(OsfTestCase):

    def test_citation_with_only_fullname(self):
        user = UserFactory()
        user.fullname = 'Martin Luther King, Jr.'
        user.family_name = ''
        user.given_name = ''
        user.middle_names = ''
        user.suffix = ''
        user.save()
        resp = user.csl_name()
        family_name = resp['family']
        given_name = resp['given']
        assert_equal(family_name, 'King')
        assert_equal(given_name, 'Martin L, Jr.')

    def test_unreg_user_can_register(self):
        user = UnregUserFactory()

        auth.register_unconfirmed(
            username=user.username,
            password='gattaca',
            fullname='Rosie',
        )

        user.reload()

        assert_true(user.get_confirmation_token(user.username))

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_confirm_email(self, mock_mail):
        user = UnregUserFactory()

        auth.register_unconfirmed(
            username=user.username,
            password='gattaca',
            fullname='Rosie'
        )

        user.reload()
        token = user.get_confirmation_token(user.username)

        res = self.app.get('/confirm/{}/{}'.format(user._id, token), allow_redirects=False)
        res = res.follow()

        assert_equal(res.status_code, 302)
        assert_in('login?service=', res.location)

        user.reload()
        mock_mail.assert_called()
        assert_equal(len(mock_mail.call_args_list), 1)
        empty, kwargs = mock_mail.call_args
        kwargs['user'].reload()

        assert_equal(empty, ())
        assert_equal(kwargs, {
            'user': user,
            'mimetype': 'html',
            'mail': mails.WELCOME,
            'to_addr': user.username,
            'osf_contact_email': settings.OSF_CONTACT_EMAIL
        })

        self.app.set_cookie(settings.COOKIE_NAME, user.get_or_create_cookie())
        res = self.app.get('/confirm/{}/{}'.format(user._id, token))

        res = res.follow()

        assert_equal(res.status_code, 302)
        assert_equal('/', urlparse.urlparse(res.location).path)
        assert_equal(len(mock_mail.call_args_list), 1)
        session = Session.objects.filter(data__auth_user_id=user._id).order_by('-modified').first()
        assert_equal(len(session.data['status']), 1)

    def test_get_user_by_id(self):
        user = UserFactory()
        assert_equal(OSFUser.load(user._id), user)

    def test_get_user_by_email(self):
        user = UserFactory()
        assert_equal(auth.get_user(email=user.username), user)

    def test_get_user_with_wrong_password_returns_false(self):
        user = UserFactory.build()
        user.set_password('killerqueen')
        assert_false(
            auth.get_user(email=user.username, password='wrong')
        )

    def test_get_user_by_external_info(self):
        service_url = 'http://localhost:5000/dashboard/'
        user, validated_credentials, cas_resp = generate_external_user_with_resp(service_url)
        user.save()
        assert_equal(auth.get_user(external_id_provider=validated_credentials['provider'], external_id=validated_credentials['id']), user)

    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_successful_external_login_cas_redirect(self, mock_service_validate, mock_get_user_from_cas_resp):
        service_url = 'http://localhost:5000/dashboard/'
        user, validated_credentials, cas_resp = generate_external_user_with_resp(service_url)
        mock_service_validate.return_value = cas_resp
        mock_get_user_from_cas_resp.return_value = (user, validated_credentials, 'authenticate')
        ticket = fake.md5()
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302, 'redirect to CAS login')
        assert_in('/login?service=', resp.location)

        # the valid username will be double quoted as it is furl quoted in both get_login_url and get_logout_url in order
        username_quoted = urllib.quote(urllib.quote(user.username, safe='@'), safe='@')
        assert_in('username={}'.format(username_quoted), resp.location)
        assert_in('verification_key={}'.format(user.verification_key), resp.location)

    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_successful_external_first_login(self, mock_service_validate, mock_get_user_from_cas_resp):
        service_url = 'http://localhost:5000/dashboard/'
        _, validated_credentials, cas_resp = generate_external_user_with_resp(service_url, user=False)
        mock_service_validate.return_value = cas_resp
        mock_get_user_from_cas_resp.return_value = (None, validated_credentials, 'external_first_login')
        ticket = fake.md5()
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302, 'redirect to external login email get')
        assert_in('/external-login/email', resp.location)

    @mock.patch('framework.auth.cas.external_first_login_authenticate')
    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_successful_external_first_login_without_attributes(self, mock_service_validate, mock_get_user_from_cas_resp, mock_external_first_login_authenticate):
        service_url = 'http://localhost:5000/dashboard/'
        user, validated_credentials, cas_resp = generate_external_user_with_resp(service_url, user=False, release=False)
        mock_service_validate.return_value = cas_resp
        mock_get_user_from_cas_resp.return_value = (None, validated_credentials, 'external_first_login')
        ticket = fake.md5()
        cas.make_response_from_ticket(ticket, service_url)
        assert_equal(user, mock_external_first_login_authenticate.call_args[0][0])

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_password_change_sends_email(self, mock_mail):
        user = UserFactory()
        user.set_password('killerqueen')
        user.save()
        assert_equal(len(mock_mail.call_args_list), 1)
        empty, kwargs = mock_mail.call_args
        kwargs['user'].reload()

        assert_equal(empty, ())
        assert_equal(kwargs, {
            'user': user,
            'mimetype': 'plain',
            'mail': mails.PASSWORD_RESET,
            'to_addr': user.username,
            'osf_contact_email': settings.OSF_CONTACT_EMAIL,
        })

    @mock.patch('framework.auth.utils.requests.post')
    def test_validate_recaptcha_success(self, req_post):
        resp = mock.Mock()
        resp.status_code = http.OK
        resp.json = mock.Mock(return_value={'success': True})
        req_post.return_value = resp
        assert_true(validate_recaptcha('a valid captcha'))

    @mock.patch('framework.auth.utils.requests.post')
    def test_validate_recaptcha_valid_req_failure(self, req_post):
        resp = mock.Mock()
        resp.status_code = http.OK
        resp.json = mock.Mock(return_value={'success': False})
        req_post.return_value = resp
        assert_false(validate_recaptcha(None))

    @mock.patch('framework.auth.utils.requests.post')
    def test_validate_recaptcha_invalid_req_failure(self, req_post):
        resp = mock.Mock()
        resp.status_code = http.BAD_REQUEST
        resp.json = mock.Mock(return_value={'success': True})
        req_post.return_value = resp
        assert_false(validate_recaptcha(None))

    @mock.patch('framework.auth.utils.requests.post')
    def test_validate_recaptcha_empty_response(self, req_post):
        req_post.side_effect=AssertionError()
        # ensure None short circuits execution (no call to google)
        assert_false(validate_recaptcha(None))

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_sign_up_twice_sends_two_confirmation_emails_only(self, mock_mail):
        # Regression test for https://openscience.atlassian.net/browse/OSF-7060
        url = api_url_for('register_user')
        sign_up_data = {
            'fullName': 'Julius Caesar',
            'email1': 'caesar@romanempire.com',
            'email2': 'caesar@romanempire.com',
            'password': 'brutusisajerk'
        }

        self.app.post_json(url, sign_up_data)
        assert_equal(len(mock_mail.call_args_list), 1)
        args, kwargs = mock_mail.call_args
        assert_equal(args, (
            'caesar@romanempire.com',
            mails.INITIAL_CONFIRM_EMAIL,
            'plain'
        ))

        self.app.post_json(url, sign_up_data)
        assert_equal(len(mock_mail.call_args_list), 2)
        args, kwargs = mock_mail.call_args
        assert_equal(args, (
            'caesar@romanempire.com',
            mails.INITIAL_CONFIRM_EMAIL,
            'plain'
        ))


class TestAuthObject(OsfTestCase):

    def test_repr(self):
        auth = AuthFactory()
        rep = repr(auth)
        assert_in(str(auth.user), rep)

    def test_factory(self):
        auth_obj = AuthFactory()
        assert_true(isinstance(auth_obj.user, OSFUser))

    def test_from_kwargs(self):
        user = UserFactory()
        request_args = {'view_only': 'mykey'}
        kwargs = {'user': user}
        auth_obj = Auth.from_kwargs(request_args, kwargs)
        assert_equal(auth_obj.user, user)
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

        self.app = WebtestApp(self.flaskapp)

        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory()
        self.link.nodes.add(self.project)
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
        self.non_contrib = AuthUserFactory()
        admin = UserFactory()
        self.public_project = ProjectFactory(is_public=True)
        self.public_project.add_contributor(admin, auth=Auth(self.public_project.creator), permissions=['read', 'write', 'admin'])
        self.private_project = ProjectFactory(is_public=False)
        self.public_project.add_contributor(self.contrib, auth=Auth(self.public_project.creator))
        self.private_project.add_contributor(self.contrib, auth=Auth(self.private_project.creator))
        self.private_project.add_contributor(admin, auth=Auth(self.private_project.creator), permissions=['read', 'write', 'admin'])
        self.public_project.save()
        self.private_project.save()

    def test_must_be_contributor_when_user_is_contributor_and_public_project(self):
        result = view_that_needs_contributor(
            pid=self.public_project._primary_key,
            user=self.contrib)
        assert_equal(result, self.public_project)

    @unittest.skip('Decorator function bug fails this test, skip until bug is fixed')
    def test_must_be_contributor_when_user_is_not_contributor_and_public_project_raise_error(self):
        with assert_raises(HTTPError):
            view_that_needs_contributor(
                pid=self.public_project._primary_key,
                user=self.non_contrib
            )

    def test_must_be_contributor_when_user_is_contributor_and_private_project(self):
        result = view_that_needs_contributor(
            pid=self.private_project._primary_key,
            user=self.contrib)
        assert_equal(result, self.private_project)

    def test_must_be_contributor_when_user_is_not_contributor_and_private_project_raise_error(self):
        with assert_raises(HTTPError):
            view_that_needs_contributor(
                pid=self.private_project._primary_key,
                user=self.non_contrib
            )

    def test_must_be_contributor_no_user_and_public_project_redirect(self):
        res = view_that_needs_contributor(
            pid=self.public_project._primary_key,
            user=None,
        )
        assert_is_redirect(res)
        # redirects to login url
        redirect_url = res.headers['Location']
        login_url = cas.get_login_url(service_url='http://localhost/')
        assert_equal(redirect_url, login_url)

    def test_must_be_contributor_no_user_and_private_project_redirect(self):
        res = view_that_needs_contributor(
            pid=self.private_project._primary_key,
            user=None,
        )
        assert_is_redirect(res)
        # redirects to login url
        redirect_url = res.headers['Location']
        login_url = cas.get_login_url(service_url='http://localhost/')
        assert_equal(redirect_url, login_url)

    def test_must_be_contributor_parent_admin_and_public_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.public_project, creator=user)
        res = view_that_needs_contributor(
            pid=self.public_project._id,
            nid=node._id,
            user=self.public_project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_admin_and_private_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.private_project, creator=user)
        res = view_that_needs_contributor(
            pid=self.private_project._id,
            nid=node._id,
            user=self.private_project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_write_public_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.public_project, creator=user)
        self.public_project.set_permissions(self.public_project.creator, ['read', 'write'])
        self.public_project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor(
                pid=self.public_project._id,
                nid=node._id,
                user=self.public_project.creator,
            )
        assert_equal(exc_info.exception.code, 403)

    def test_must_be_contributor_parent_write_private_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.private_project, creator=user)
        self.private_project.set_permissions(self.private_project.creator, ['read', 'write'])
        self.private_project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor(
                pid=self.private_project._id,
                nid=node._id,
                user=self.private_project.creator,
            )
        assert_equal(exc_info.exception.code, 403)


@must_be_contributor_or_public
def view_that_needs_contributor_or_public(**kwargs):
    return kwargs.get('node') or kwargs.get('parent')


class TestMustBeContributorOrPublicDecorator(AuthAppTestCase):

    def setUp(self):
        super(TestMustBeContributorOrPublicDecorator, self).setUp()
        self.contrib = AuthUserFactory()
        self.non_contrib = AuthUserFactory()
        self.public_project = ProjectFactory(is_public=True)
        self.private_project = ProjectFactory(is_public=False)
        self.public_project.add_contributor(self.contrib, auth=Auth(self.public_project.creator))
        self.private_project.add_contributor(self.contrib, auth=Auth(self.private_project.creator))
        self.public_project.save()
        self.private_project.save()

    def test_must_be_contributor_when_user_is_contributor_and_public_project(self):
        result = view_that_needs_contributor_or_public(
            pid=self.public_project._primary_key,
            user=self.contrib)
        assert_equal(result, self.public_project)

    def test_must_be_contributor_when_user_is_not_contributor_and_public_project(self):
        result = view_that_needs_contributor_or_public(
            pid=self.public_project._primary_key,
            user=self.non_contrib)
        assert_equal(result, self.public_project)

    def test_must_be_contributor_when_user_is_contributor_and_private_project(self):
        result = view_that_needs_contributor_or_public(
            pid=self.private_project._primary_key,
            user=self.contrib)
        assert_equal(result, self.private_project)

    def test_must_be_contributor_when_user_is_not_contributor_and_private_project_raise_error(self):
        with assert_raises(HTTPError):
            view_that_needs_contributor_or_public(
                pid=self.private_project._primary_key,
                user=self.non_contrib
            )

    def test_must_be_contributor_no_user_and_public_project(self):
        res = view_that_needs_contributor_or_public(
            pid=self.public_project._primary_key,
            user=None,
        )
        assert_equal(res, self.public_project)

    def test_must_be_contributor_no_user_and_private_project(self):
        res = view_that_needs_contributor_or_public(
            pid=self.private_project._primary_key,
            user=None,
        )
        assert_is_redirect(res)
        # redirects to login url
        redirect_url = res.headers['Location']
        login_url = cas.get_login_url(service_url='http://localhost/')
        assert_equal(redirect_url, login_url)

    def test_must_be_contributor_parent_admin_and_public_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.public_project, creator=user)
        res = view_that_needs_contributor_or_public(
            pid=self.public_project._id,
            nid=node._id,
            user=self.public_project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_admin_and_private_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.private_project, creator=user)
        res = view_that_needs_contributor_or_public(
            pid=self.private_project._id,
            nid=node._id,
            user=self.private_project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_write_public_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.public_project, creator=user)
        contrib = UserFactory()
        self.public_project.add_contributor(contrib, auth=Auth(self.public_project.creator), permissions=['read', 'write'])
        self.public_project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor_or_public(
                pid=self.public_project._id,
                nid=node._id,
                user=contrib,
            )
        assert_equal(exc_info.exception.code, 403)

    def test_must_be_contributor_parent_write_private_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.private_project, creator=user)
        contrib = UserFactory()
        self.private_project.add_contributor(contrib, auth=Auth(self.private_project.creator), permissions=['read', 'write'])
        self.private_project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor_or_public(
                pid=self.private_project._id,
                nid=node._id,
                user=contrib,
            )
        assert_equal(exc_info.exception.code, 403)


@must_be_contributor_or_public_but_not_anonymized
def view_that_needs_contributor_or_public_but_not_anonymized(**kwargs):
    return kwargs.get('node') or kwargs.get('parent')


class TestMustBeContributorOrPublicButNotAnonymizedDecorator(AuthAppTestCase):
    def setUp(self):
        super(TestMustBeContributorOrPublicButNotAnonymizedDecorator, self).setUp()
        self.contrib = AuthUserFactory()
        self.non_contrib = AuthUserFactory()
        admin = UserFactory()
        self.public_project = ProjectFactory(is_public=True)
        self.public_project.add_contributor(admin, auth=Auth(self.public_project.creator), permissions=['read', 'write', 'admin'])
        self.private_project = ProjectFactory(is_public=False)
        self.private_project.add_contributor(admin, auth=Auth(self.private_project.creator), permissions=['read', 'write', 'admin'])
        self.public_project.add_contributor(self.contrib, auth=Auth(self.public_project.creator))
        self.private_project.add_contributor(self.contrib, auth=Auth(self.private_project.creator))
        self.public_project.save()
        self.private_project.save()
        self.anonymized_link_to_public_project = PrivateLinkFactory(anonymous=True)
        self.anonymized_link_to_private_project = PrivateLinkFactory(anonymous=True)
        self.anonymized_link_to_public_project.nodes.add(self.public_project)
        self.anonymized_link_to_public_project.save()
        self.anonymized_link_to_private_project.nodes.add(self.private_project)
        self.anonymized_link_to_private_project.save()
        self.flaskapp = Flask('Testing decorator')

        @self.flaskapp.route('/project/<pid>/')
        @must_be_contributor_or_public_but_not_anonymized
        def project_get(**kwargs):
            return 'success', 200
        self.app = WebtestApp(self.flaskapp)

    def test_must_be_contributor_when_user_is_contributor_and_public_project(self):
        result = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.public_project._primary_key,
            user=self.contrib)
        assert_equal(result, self.public_project)

    def test_must_be_contributor_when_user_is_not_contributor_and_public_project(self):
        result = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.public_project._primary_key,
            user=self.non_contrib)
        assert_equal(result, self.public_project)

    def test_must_be_contributor_when_user_is_contributor_and_private_project(self):
        result = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.private_project._primary_key,
            user=self.contrib)
        assert_equal(result, self.private_project)

    def test_must_be_contributor_when_user_is_not_contributor_and_private_project_raise_error(self):
        with assert_raises(HTTPError):
            view_that_needs_contributor_or_public_but_not_anonymized(
                pid=self.private_project._primary_key,
                user=self.non_contrib
            )

    def test_must_be_contributor_no_user_and_public_project(self):
        res = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.public_project._primary_key,
            user=None,
        )
        assert_equal(res, self.public_project)

    def test_must_be_contributor_no_user_and_private_project(self):
        res = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.private_project._primary_key,
            user=None,
        )
        assert_is_redirect(res)
        # redirects to login url
        redirect_url = res.headers['Location']
        login_url = cas.get_login_url(service_url='http://localhost/')
        assert_equal(redirect_url, login_url)

    def test_must_be_contributor_parent_admin_and_public_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.public_project, creator=user)
        res = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.public_project._id,
            nid=node._id,
            user=self.public_project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_admin_and_private_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.private_project, creator=user)
        res = view_that_needs_contributor_or_public_but_not_anonymized(
            pid=self.private_project._id,
            nid=node._id,
            user=self.private_project.creator,
        )
        assert_equal(res, node)

    def test_must_be_contributor_parent_write_public_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.public_project, creator=user)
        self.public_project.set_permissions(self.public_project.creator, ['read', 'write'])
        self.public_project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor_or_public_but_not_anonymized(
                pid=self.public_project._id,
                nid=node._id,
                user=self.public_project.creator,
            )
        assert_equal(exc_info.exception.code, 403)

    def test_must_be_contributor_parent_write_private_project(self):
        user = UserFactory()
        node = NodeFactory(parent=self.private_project, creator=user)
        self.private_project.set_permissions(self.private_project.creator, ['read', 'write'])
        self.private_project.save()
        with assert_raises(HTTPError) as exc_info:
            view_that_needs_contributor_or_public_but_not_anonymized(
                pid=self.private_project._id,
                nid=node._id,
                user=self.private_project.creator,
            )
        assert_equal(exc_info.exception.code, 403)

    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_decorator_does_allow_anonymous_link_public_project(self, mock_from_kwargs):
        mock_from_kwargs.return_value = Auth(user=None)
        res = self.app.get('/project/{0}'.format(self.public_project._primary_key),
            {'view_only': self.anonymized_link_to_public_project.key})
        res = res.follow()
        assert_equal(res.status_code, 200)

    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_decorator_does_not_allow_anonymous_link_private_project(self, mock_from_kwargs):
        mock_from_kwargs.return_value = Auth(user=None)
        res = self.app.get('/project/{0}'.format(self.private_project._primary_key),
                           {'view_only': self.anonymized_link_to_private_project.key})
        res = res.follow(expect_errors=True)
        assert_equal(res.status_code, 500)

@must_be_logged_in
def protected(**kwargs):
    return 'open sesame'


@must_have_permission('admin')
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
        assert_equal(login_url, resp.headers.get('location'))

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_true(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user, permissions=[permissions.READ, permissions.WRITE, permissions.ADMIN],
                                auth=Auth(project.creator))
        mock_from_kwargs.return_value = Auth(user=user)
        mock_to_nodes.return_value = (None, project)
        thriller(node=project)

    @mock.patch('website.project.decorators._kwargs_to_nodes')
    @mock.patch('framework.auth.decorators.Auth.from_kwargs')
    def test_must_have_permission_false(self, mock_from_kwargs, mock_to_nodes):
        project = ProjectFactory()
        user = UserFactory()
        mock_from_kwargs.return_value = Auth(user=user)
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
        node_settings.save()

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
        node_settings.save()

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


if __name__ == '__main__':
    unittest.main()
