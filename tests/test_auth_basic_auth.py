#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Basic Authorization tests for the OSF.'''

from __future__ import absolute_import
import unittest
import mock

from nose.tools import *  # noqa PEP8 asserts

from website.addons.twofactor.tests import _valid_code
from website.util import web_url_for
from website import settings

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory


class TestAuthBasicAuthentication(OsfTestCase):

    TOTP_SECRET = 'b8f85986068f8079aa9d'

    def setUp(self):
        super(TestAuthBasicAuthentication, self).setUp()
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        # Test projects for which a given user DOES and DOES NOT have appropriate permissions
        self.reachable_project = ProjectFactory(title="Private Project User 1", is_public=False, creator=self.user1)
        self.unreachable_project = ProjectFactory(title="Private Project User 2", is_public=False, creator=self.user2)
        self.reachable_url = self.reachable_project.web_url_for('view_project')
        self.unreachable_url = self.unreachable_project.web_url_for('view_project')

        # Test dashboard and myprojects redirection
        self.dashboard_url = web_url_for('dashboard')
        self.myprojects_url = web_url_for('my_projects')

    def test_missing_credential_fails(self):
        res = self.app.get(self.unreachable_url, auth=None, expect_errors=True)
        assert_equal(res.status_code, 302)
        assert_true('Location' in res.headers)
        assert_true('/login' in res.headers['Location'])

    def test_invalid_credential_fails(self):
        res = self.app.get(self.unreachable_url, auth=(self.user1.username, 'invalid password'), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_true('<h2 id=\'error\' data-http-status-code="401">Unauthorized</h2>' in res.body)

    def test_valid_credential_authenticates_and_has_permissions(self):
        res = self.app.get(self.reachable_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)

    def test_valid_credential_authenticates_but_user_lacks_object_permissions(self):
        res = self.app.get(self.unreachable_url, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_valid_credential_but_twofactor_required(self):
        user1_addon = self.user1.get_or_add_addon('twofactor')
        user1_addon.totp_drift = 1
        user1_addon.totp_secret = self.TOTP_SECRET
        user1_addon.is_confirmed = True
        user1_addon.save()

        res = self.app.get(self.reachable_url, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_true('<h2 id=\'error\' data-http-status-code="401">Unauthorized</h2>' in res.body)

    def test_valid_credential_twofactor_invalid_otp(self):
        user1_addon = self.user1.get_or_add_addon('twofactor')
        user1_addon.totp_drift = 1
        user1_addon.totp_secret = self.TOTP_SECRET
        user1_addon.is_confirmed = True
        user1_addon.save()

        res = self.app.get(self.reachable_url, auth=self.user1.auth, headers={'X-OSF-OTP': 'invalid otp'}, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_true('<h2 id=\'error\' data-http-status-code="401">Unauthorized</h2>' in res.body)

    def test_valid_credential_twofactor_valid_otp(self):
        user1_addon = self.user1.get_or_add_addon('twofactor')
        user1_addon.totp_drift = 1
        user1_addon.totp_secret = self.TOTP_SECRET
        user1_addon.is_confirmed = True
        user1_addon.save()

        res = self.app.get(self.reachable_url, auth=self.user1.auth, headers={'X-OSF-OTP': _valid_code(self.TOTP_SECRET)})
        assert_equal(res.status_code, 200)

    def test_dashboard_with_valid_cookie(self):
        cookie = self.user1.get_or_create_cookie()
        self.app.set_cookie(settings.COOKIE_NAME, str(cookie))
        res = self.app.get(self.dashboard_url)
        assert_equal(res.status_code, 302)
        assert_not_in('login', res.location)

    def test_dashboard_without_cookie(self):
        res = self.app.get(self.dashboard_url)
        assert_equal(res.status_code, 302)
        assert_in('login?service=', res.location)
        assert_in('dashboard/', res.location.split('?')[1])

    def test_myprojects_with_valid_cookie(self):
        cookie = self.user1.get_or_create_cookie()
        self.app.set_cookie(settings.COOKIE_NAME, str(cookie))
        res = self.app.get(self.myprojects_url)
        assert_equal(res.status_code, 200)

    def test_myprojects_without_cookie(self):
        res = self.app.get(self.myprojects_url)
        assert_equal(res.status_code, 302)
        assert_in('login?service=', res.location)
        assert_in('myprojects/', res.location.split('?')[1])
