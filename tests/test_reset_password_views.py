#!/usr/bin/env python3
"""Views tests for the OSF."""
from unittest import mock
from urllib.parse import quote_plus
from framework.auth import core

import pytest
from django.utils import timezone
from tests.utils import run_celery_tasks

from framework.auth import cas
from osf_tests.factories import (
    AuthUserFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)
from website.util import web_url_for

pytestmark = pytest.mark.django_db

class TestResetPassword(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.another_user = AuthUserFactory()
        self.osf_key_v2 = core.generate_verification_key(verification_type='password')
        self.user.verification_key_v2 = self.osf_key_v2
        self.user.verification_key = None
        self.user.save()
        self.get_url = web_url_for(
            'reset_password_get',
            uid=self.user._id,
            token=self.osf_key_v2['token']
        )
        self.get_url_invalid_key = web_url_for(
            'reset_password_get',
            uid=self.user._id,
            token=core.generate_verification_key()
        )
        self.get_url_invalid_user = web_url_for(
            'reset_password_get',
            uid=self.another_user._id,
            token=self.osf_key_v2['token']
        )

    # successfully load reset password page
    def test_reset_password_view_returns_200(self):
        res = self.app.get(self.get_url)
        assert res.status_code == 200

    # raise http 400 error
    def test_reset_password_view_raises_400(self):
        res = self.app.get(self.get_url_invalid_key)
        assert res.status_code == 400

        res = self.app.get(self.get_url_invalid_user)
        assert res.status_code == 400

        self.user.verification_key_v2['expires'] = timezone.now()
        self.user.save()
        res = self.app.get(self.get_url)
        assert res.status_code == 400

    # successfully reset password
    @pytest.mark.enable_enqueue_task
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_can_reset_password_if_form_success(self, mock_service_validate):
        # TODO: check in qa url encoding
        # load reset password page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('resetPasswordForm')
        form['password'] = 'newpassword'
        form['password2'] = 'newpassword'
        res = form.submit(self.app)

        # check request URL is /resetpassword with username and new verification_key_v2 token
        request_url_path = res.request.path
        assert 'resetpassword' in request_url_path
        assert self.user._id in request_url_path
        assert self.user.verification_key_v2['token'] in request_url_path

        # check verification_key_v2 for OSF is destroyed and verification_key for CAS is in place
        self.user.reload()
        assert self.user.verification_key_v2 == {}
        assert not self.user.verification_key is None

        # check redirection to CAS login with username and the new verification_key(CAS)
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'login?service=' in location
        assert f'username={quote_plus(self.user.username)}' in location
        assert f'verification_key={self.user.verification_key}' in location

        # check if password was updated
        self.user.reload()
        assert self.user.check_password('newpassword')

        # check if verification_key is destroyed after service validation
        mock_service_validate.return_value = cas.CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={'accessToken': fake.md5()}
        )
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        with run_celery_tasks():
            cas.make_response_from_ticket(ticket, service_url)
        self.user.reload()
        assert self.user.verification_key is None

    #  log users out before they land on reset password page
    def test_reset_password_logs_out_user(self):
        # visit reset password link while another user is logged in
        res = self.app.get(self.get_url, auth=self.another_user.auth)
        # check redirection to CAS logout
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'reauth' not in location
        assert 'logout?service=' in location
        assert 'resetpassword' in location

