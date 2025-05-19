#!/usr/bin/env python3
"""Views tests for the OSF."""
from unittest.mock import MagicMock, ANY

import datetime as dt
from unittest import mock
from urllib.parse import quote_plus
from framework.auth import core

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from flask import request
from rest_framework import status as http_status
from tests.utils import run_celery_tasks

from framework import auth
from framework.auth import Auth, cas
from framework.auth.campaigns import (
    get_campaigns,
    is_institution_login,
    is_native_login,
    is_proxy_login,
    campaign_url_for
)
from framework.auth.exceptions import InvalidTokenError
from framework.auth.views import login_and_register_handler
from osf.models import OSFUser, NotableDomain
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
    UserFactory,
    UnconfirmedUserFactory,
)
from tests.base import (
    capture_signals,
    fake,
    OsfTestCase,
)
from website import mails, settings
from website.util import api_url_for, web_url_for

pytestmark = pytest.mark.django_db

class TestAuthViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_ok(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.fullname == name
        assert user.accepted_terms_of_service is None

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2902
    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_email_case_insensitive(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': str(email).upper(),
                'password': password,
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.fullname == name

    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_email_with_accepted_tos(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
                'acceptedTermsOfService': True
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.accepted_terms_of_service

    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_email_without_accepted_tos(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
                'acceptedTermsOfService': False
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.accepted_terms_of_service is None

    @mock.patch('framework.auth.views.send_confirm_email_async')
    def test_register_scrubs_username(self, _):
        url = api_url_for('register_user')
        name = "<i>Eunice</i> O' \"Cornwallis\"<script type='text/javascript' src='http://www.cornify.com/js/cornify.js'></script><script type='text/javascript'>cornify_add()</script>"
        email, password = fake_email(), 'underpressure'
        res = self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )

        expected_scrub_username = "Eunice O' \"Cornwallis\"cornify_add()"
        user = OSFUser.objects.get(username=email)

        assert res.status_code == http_status.HTTP_200_OK
        assert user.fullname == expected_scrub_username

    def test_register_email_mismatch(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        res = self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email + 'lol',
                'password': password,
            },
        )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST
        users = OSFUser.objects.filter(username=email)
        assert users.count() == 0

    def test_register_email_already_registered(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), fake.password()
        existing_user = UserFactory(
            username=email,
        )
        res = self.app.post(
            url, json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password
            },

        )
        assert res.status_code == http_status.HTTP_409_CONFLICT
        users = OSFUser.objects.filter(username=email)
        assert users.count() == 1

    def test_register_blocked_email_domain(self):
        NotableDomain.objects.get_or_create(
            domain='mailinator.com',
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )
        url = api_url_for('register_user')
        name, email, password = fake.name(), 'bad@mailinator.com', 'agreatpasswordobviously'
        res = self.app.post(
            url, json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password
            },

        )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST
        users = OSFUser.objects.filter(username=email)
        assert users.count() == 0

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=True)
    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_good_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        captcha = 'some valid captcha'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    'g-recaptcha-response': captcha,
                }
            )
            validate_recaptcha.assert_called_with(captcha, remote_ip='127.0.0.1')
            assert resp.status_code == http_status.HTTP_200_OK
            user = OSFUser.objects.get(username=email)
            assert user.fullname == name

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=False)
    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_missing_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    # 'g-recaptcha-response': 'supposed to be None',
                },
            )
            validate_recaptcha.assert_called_with(None, remote_ip='127.0.0.1')
            assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=False)
    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_register_bad_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    'g-recaptcha-response': 'bad captcha',
                },

            )
            assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_register_after_being_invited_as_unreg_contributor(self, mock_update_search_nodes):
        # Regression test for:
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/861
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/1021
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/1026
        # A user is invited as an unregistered contributor
        project = ProjectFactory()

        name, email = fake.name(), fake_email()

        project.add_unregistered_contributor(fullname=name, email=email, auth=Auth(project.creator))
        project.save()

        # The new, unregistered user
        new_user = OSFUser.objects.get(username=email)

        # Instead of following the invitation link, they register at the regular
        # registration page

        # They use a different name when they register, but same email
        real_name = fake.name()
        password = 'myprecious'

        url = api_url_for('register_user')
        payload = {
            'fullName': real_name,
            'email1': email,
            'email2': email,
            'password': password,
        }
        # Send registration request
        self.app.post(url, json=payload)

        new_user.reload()

        # New user confirms by following confirmation link
        confirm_url = new_user.get_confirmation_url(email, external=False)
        self.app.get(confirm_url)

        new_user.reload()
        # Password and fullname should be updated
        assert new_user.is_confirmed
        assert new_user.check_password(password)
        assert new_user.fullname == real_name

    @mock.patch('framework.auth.views.send_confirm_email')
    def test_register_sends_user_registered_signal(self, mock_send_confirm_email):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with capture_signals() as mock_signals:
            self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': email,
                    'password': password,
                }
            )
        assert mock_signals.signals_sent() == {auth.signals.user_registered, auth.signals.unconfirmed_user_created}
        assert mock_send_confirm_email.called

    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_resend_confirmation(self, send_mail: MagicMock):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert send_mail.called
        send_mail.assert_called_with(
            email,
            mails.CONFIRM_EMAIL,
            user=self.user,
            confirmation_url=ANY,
            email='test@mail.com',
            merge_target=None,
            external_id_provider=None,
            branded_preprints_provider=None,
            osf_support_email=settings.OSF_SUPPORT_EMAIL,
            can_change_preferences=False,
            logo='osf_logo'
        )
        self.user.reload()
        assert token != self.user.get_confirmation_token(email)
        with pytest.raises(InvalidTokenError):
            self.user.get_unconfirmed_email_for_token(token)

    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_click_confirmation_email(self, send_mail):
        # TODO: check in qa url encoding
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        res = self.app.get(url)
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == True
        assert res.status_code == 302
        login_url = quote_plus('login?service')
        assert login_url in res.text

    def test_get_email_to_add_no_email(self):
        email_verifications = self.user.unconfirmed_email_info
        assert email_verifications == []

    def test_get_unconfirmed_email(self):
        email = 'test@mail.com'
        self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        assert email_verifications == []

    def test_get_email_to_add(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == True
        email_verifications = self.user.unconfirmed_email_info
        assert email_verifications[0]['address'] == 'test@mail.com'

    def test_add_email(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put(put_email_url, json=email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert res.json['status'] == 'success'
        assert self.user.emails.last().address == 'test@mail.com'

    def test_remove_email(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        remove_email_url = api_url_for('unconfirmed_email_remove')
        remove_res = self.app.delete(remove_email_url, json=email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert remove_res.json['status'] == 'success'
        assert self.user.unconfirmed_email_info == []

    def test_add_expired_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.email_verifications[token]['expiration'] = timezone.now() - dt.timedelta(days=100)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['email'] == email
        self.user.clean_email_verifications(given_token=token)
        unconfirmed_emails = self.user.unconfirmed_email_info
        assert unconfirmed_emails == []
        assert self.user.email_verifications == {}

    def test_clean_email_verifications(self):
        # Do not return bad token and removes it from user.email_verifications
        email = 'test@mail.com'
        token = 'blahblahblah'
        self.user.email_verifications[token] = {'expiration': timezone.now() + dt.timedelta(days=1),
                                                'email': email,
                                                'confirmed': False }
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['email'] == email
        self.user.clean_email_verifications(given_token=token)
        unconfirmed_emails = self.user.unconfirmed_email_info
        assert unconfirmed_emails == []
        assert self.user.email_verifications == {}

    def test_clean_email_verifications_when_email_verifications_is_an_empty_dict(self):
        self.user.email_verifications = {}
        self.user.save()
        ret = self.user.clean_email_verifications()
        assert ret is None
        assert self.user.email_verifications == {}

    def test_add_invalid_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = '\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello@yourmom.com'
        # illegal_str = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello'
        # illegal_str += unichr(0xd800) + unichr(0xdbff) + ' World'
        # email = 'test@mail.com'
        with pytest.raises(ValidationError):
            self.user.add_unconfirmed_email(email)

    def test_add_email_merge(self):
        email = 'copy@cat.com'
        dupe = UserFactory(
            username=email,
        )
        dupe.save()
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put(put_email_url, json=email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert res.json['status'] == 'success'
        assert self.user.emails.last().address == 'copy@cat.com'

    def test_resend_confirmation_without_user_id(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        res = self.app.put(url, json={'email': header}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == '"id" is required'

    def test_resend_confirmation_without_email(self):
        url = api_url_for('resend_confirmation')
        res = self.app.put(url, json={'id': self.user._id}, auth=self.user.auth)
        assert res.status_code == 400

    def test_resend_confirmation_not_work_for_primary_email(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': True, 'confirmed': False}
        res = self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == 'Cannnot resend confirmation for confirmed emails'

    def test_resend_confirmation_not_work_for_confirmed_email(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': True}
        res = self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == 'Cannnot resend confirmation for confirmed emails'

    @mock.patch('framework.auth.views.mails.execute_email_send')
    def test_resend_confirmation_does_not_send_before_throttle_expires(self, send_mail):
        email = 'test@mail.com'
        self.user.save()
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert send_mail.called
        # 2nd call does not send email because throttle period has not expired
        res = self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert res.status_code == 400

    def test_confirm_email_clears_unclaimed_records_and_revokes_token(self):
        unclaimed_user = UnconfirmedUserFactory()
        # unclaimed user has been invited to a project.
        referrer = UserFactory()
        project = ProjectFactory(creator=referrer)
        unclaimed_user.add_unclaimed_record(project, referrer, 'foo')
        unclaimed_user.save()

        # sanity check
        assert len(unclaimed_user.email_verifications.keys()) == 1

        # user goes to email confirmation link
        token = unclaimed_user.get_confirmation_token(unclaimed_user.username)
        url = web_url_for('confirm_email_get', uid=unclaimed_user._id, token=token)
        res = self.app.get(url)
        assert res.status_code == 302

        # unclaimed records and token are cleared
        unclaimed_user.reload()
        assert unclaimed_user.unclaimed_records == {}
        assert len(unclaimed_user.email_verifications.keys()) == 0

    def test_confirmation_link_registers_user(self):
        user = OSFUser.create_unconfirmed('brian@queen.com', 'bicycle123', 'Brian May')
        assert not user.is_registered  # sanity check
        user.save()
        confirmation_url = user.get_confirmation_url('brian@queen.com', external=False)
        res = self.app.get(confirmation_url)
        assert res.status_code == 302, 'redirects to settings page'
        res = self.app.get(confirmation_url, follow_redirects=True)
        user.reload()
        assert user.is_registered


class TestAuthLoginAndRegisterLogic(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.no_auth = Auth()
        self.user_auth = AuthUserFactory()
        self.auth = Auth(user=self.user_auth)
        self.next_url = web_url_for('my_projects', _absolute=True)
        self.invalid_campaign = 'invalid_campaign'

    def test_osf_login_with_auth(self):
        # login: user with auth
        data = login_and_register_handler(self.auth)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_osf_login_without_auth(self):
        # login: user without auth
        data = login_and_register_handler(self.no_auth)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_osf_register_with_auth(self):
        # register: user with auth
        data = login_and_register_handler(self.auth, login=False)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_osf_register_without_auth(self):
        # register: user without auth
        data = login_and_register_handler(self.no_auth, login=False)
        assert data.get('status_code') == http_status.HTTP_200_OK
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_next_url_login_with_auth(self):
        # next_url login: user with auth
        data = login_and_register_handler(self.auth, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == self.next_url

    def test_next_url_login_without_auth(self):
        # login: user without auth
        request.url = web_url_for('auth_login', next=self.next_url, _absolute=True)
        data = login_and_register_handler(self.no_auth, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(request.url)

    def test_next_url_register_with_auth(self):
        # register: user with auth
        data = login_and_register_handler(self.auth, login=False, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == self.next_url

    def test_next_url_register_without_auth(self):
        # register: user without auth
        data = login_and_register_handler(self.no_auth, login=False, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_200_OK
        assert data.get('next_url') == request.url

    def test_institution_login_and_register(self):
        pass

    def test_institution_login_with_auth(self):
        # institution login: user with auth
        data = login_and_register_handler(self.auth, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_institution_login_without_auth(self):
        # institution login: user without auth
        data = login_and_register_handler(self.no_auth, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(web_url_for('dashboard', _absolute=True),
                                                         campaign='institution')

    def test_institution_login_next_url_with_auth(self):
        # institution login: user with auth and next url
        data = login_and_register_handler(self.auth, next_url=self.next_url, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == self.next_url

    def test_institution_login_next_url_without_auth(self):
        # institution login: user without auth and next url
        data = login_and_register_handler(self.no_auth, next_url=self.next_url ,campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(self.next_url, campaign='institution')

    def test_institution_regsiter_with_auth(self):
        # institution register: user with auth
        data = login_and_register_handler(self.auth, login=False, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_institution_register_without_auth(self):
        # institution register: user without auth
        data = login_and_register_handler(self.no_auth, login=False, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(web_url_for('dashboard', _absolute=True), campaign='institution')

    def test_campaign_login_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user with auth
            data = login_and_register_handler(self.auth, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == campaign_url_for(campaign)

    def test_campaign_login_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user without auth
            data = login_and_register_handler(self.no_auth, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == web_url_for('auth_register', campaign=campaign,
                                                       next=campaign_url_for(campaign))

    def test_campaign_register_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user with auth
            data = login_and_register_handler(self.auth, login=False, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == campaign_url_for(campaign)

    def test_campaign_register_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user without auth
            data = login_and_register_handler(self.no_auth, login=False, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_200_OK
            if is_native_login(campaign):
                # native campaign: prereg and erpc
                assert data.get('next_url') == campaign_url_for(campaign)
            elif is_proxy_login(campaign):
                # proxy campaign: preprints and branded ones
                assert data.get('next_url') == web_url_for('auth_login', next=campaign_url_for(campaign),
                                                           _absolute=True)

    def test_campaign_next_url_login_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user with auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.auth, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == next_url

    def test_campaign_next_url_login_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user without auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.no_auth, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == web_url_for('auth_register', campaign=campaign, next=next_url)

    def test_campaign_next_url_register_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user with auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.auth, login=False, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == next_url

    def test_campaign_next_url_register_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user without auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.no_auth, login=False, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_200_OK
            if is_native_login(campaign):
                # native campaign: prereg and erpc
                assert data.get('next_url') == next_url
            elif is_proxy_login(campaign):
                # proxy campaign: preprints and branded ones
                assert data.get('next_url') == web_url_for('auth_login', next= next_url, _absolute=True)

    def test_invalid_campaign_login_without_auth(self):
        data = login_and_register_handler(
            self.no_auth,
            login=True,
            campaign=self.invalid_campaign,
            next_url=self.next_url
        )
        redirect_url = web_url_for('auth_login', campaigns=None, next=self.next_url)
        assert data['status_code'] == http_status.HTTP_302_FOUND
        assert data['next_url'] == redirect_url
        assert data['campaign'] is None

    def test_invalid_campaign_register_without_auth(self):
        data = login_and_register_handler(
            self.no_auth,
            login=False,
            campaign=self.invalid_campaign,
            next_url=self.next_url
        )
        redirect_url = web_url_for('auth_register', campaigns=None, next=self.next_url)
        assert data['status_code'] == http_status.HTTP_302_FOUND
        assert data['next_url'] == redirect_url
        assert data['campaign'] is None

    # The following two tests handles the special case for `claim_user_registered`
    # When an authenticated user clicks the claim confirmation clink, there are two ways to trigger this flow:
    # 1. If the authenticated user is already a contributor to the project, OSF will ask the user to sign out
    #    by providing a "logout" link.
    # 2. If the authenticated user is not a contributor but decides not to claim contributor under this account,
    #    OSF provides a link "not <username>?" for the user to logout.
    # Both links will land user onto the register page with "MUST LOGIN" push notification.
    def test_register_logout_flag_with_auth(self):
        # when user click the "logout" or "not <username>?" link, first step is to log user out
        data = login_and_register_handler(self.auth, login=False, campaign=None, next_url=self.next_url, logout=True)
        assert data.get('status_code') == 'auth_logout'
        assert data.get('next_url') == self.next_url

    def test_register_logout_flage_without(self):
        # the second step is to land user on register page with "MUST LOGIN" warning
        data = login_and_register_handler(self.no_auth, login=False, campaign=None, next_url=self.next_url, logout=True)
        assert data.get('status_code') == http_status.HTTP_200_OK
        assert data.get('next_url') == self.next_url
        assert data.get('must_login_warning')


class TestAuthLogout(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.goodbye_url = web_url_for('goodbye', _absolute=True)
        self.redirect_url = web_url_for('forgot_password_get', _absolute=True)
        self.valid_next_url = web_url_for('dashboard', _absolute=True)
        self.invalid_next_url = 'http://localhost:1234/abcde'
        self.auth_user = AuthUserFactory()

    def tearDown(self):
        super().tearDown()
        OSFUser.objects.all().delete()
        assert OSFUser.objects.count() == 0

    def test_logout_with_valid_next_url_logged_in(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.valid_next_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(logout_url) == resp.headers['Location']

    def test_logout_with_valid_next_url_logged_out(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.valid_next_url)
        resp = self.app.get(logout_url, auth=None)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert self.valid_next_url == resp.headers['Location']

    def test_logout_with_invalid_next_url_logged_in(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.invalid_next_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.goodbye_url) == resp.headers['Location']

    def test_logout_with_invalid_next_url_logged_out(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.invalid_next_url)
        resp = self.app.get(logout_url, auth=None)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.goodbye_url) == resp.headers['Location']

    def test_logout_with_redirect_url(self):
        logout_url = web_url_for('auth_logout', _absolute=True, redirect_url=self.redirect_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.redirect_url) == resp.headers['Location']

    def test_logout_with_no_parameter(self):
        logout_url = web_url_for('auth_logout', _absolute=True)
        resp = self.app.get(logout_url, auth=None)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.goodbye_url) == resp.headers['Location']


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
