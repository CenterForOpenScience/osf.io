from urllib.parse import quote_plus

from osf.models import NotificationType
from tests.base import OsfTestCase
from osf_tests.factories import (
    AuthUserFactory,
    UserFactory,
)
from tests.utils import capture_notifications
from website.util import web_url_for
from tests.test_webtests import assert_in_html, assert_not_in_html

class TestForgotPassword(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.auth_user = AuthUserFactory()
        self.get_url = web_url_for('forgot_password_get')
        self.post_url = web_url_for('forgot_password_post')
        self.user.verification_key_v2 = {}
        self.user.save()


    # log users out before they land on forgot password page
    def test_forgot_password_logs_out_user(self):
        # visit forgot password link while another user is logged in
        res = self.app.get(self.get_url, auth=self.auth_user.auth)
        # check redirection to CAS logout
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'reauth' not in location
        assert 'logout?service=' in location
        assert 'forgotpassword' in location

    # test that forgot password page is loaded correctly
    def test_get_forgot_password(self):
        res = self.app.get(self.get_url)
        assert res.status_code == 200
        assert 'Forgot Password' in res.text
        assert res.get_form('forgotPasswordForm')

    # test that existing user can receive reset password email
    def test_can_receive_reset_password_email(self):
        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('forgotPasswordForm')
        form['forgot_password-email'] = self.user.username
        with capture_notifications() as notifications:
            res = form.submit(self.app)
        # check mail was sent
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_FORGOT_PASSWORD
        # check http 200 response
        assert res.status_code == 200
        # check request URL is /forgotpassword
        assert res.request.path == self.post_url
        # check push notification
        assert_in_html('If there is an OSF account', res.text)
        assert_not_in_html('Please wait', res.text)

        # check verification_key_v2 is set
        self.user.reload()
        assert self.user.verification_key_v2 != {}

    # test that non-existing user cannot receive reset password email
    def test_cannot_receive_reset_password_email(self):
        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('forgotPasswordForm')
        form['forgot_password-email'] = 'fake' + self.user.username
        with capture_notifications() as notifications:
            res = form.submit(self.app)

        # check mail was not sent
        assert notifications == {'emits': [], 'emails': []}
        # check http 200 response
        assert res.status_code == 200
        # check request URL is /forgotpassword
        assert res.request.path == self.post_url
        # check push notification
        assert_in_html('If there is an OSF account', res.text)
        assert_not_in_html('Please wait', res.text)

        # check verification_key_v2 is not set
        self.user.reload()
        assert self.user.verification_key_v2 == {}

    # test that non-existing user cannot receive reset password email
    def test_not_active_user_no_reset_password_email(self):
        self.user.deactivate_account()
        self.user.save()

        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('forgotPasswordForm')
        form['forgot_password-email'] = self.user.username
        with capture_notifications() as notifications:
            res = form.submit(self.app)

        # check mail was not sent
        assert notifications == {'emails': [], 'emits': []}
        # check http 200 response
        assert res.status_code == 200
        # check request URL is /forgotpassword
        assert res.request.path == self.post_url
        # check push notification
        assert_in_html('If there is an OSF account', res.text)
        assert_not_in_html('Please wait', res.text)

        # check verification_key_v2 is not set
        self.user.reload()
        assert self.user.verification_key_v2 == {}

    # test that user cannot submit forgot password request too quickly
    def test_cannot_reset_password_twice_quickly(self):
        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('forgotPasswordForm')
        form['forgot_password-email'] = self.user.username
        res = form.submit(self.app)
        res = form.submit(self.app)

        # check http 200 response
        assert res.status_code == 200
        # check push notification
        assert_in_html('Please wait', res.text)
        assert_not_in_html('If there is an OSF account', res.text)


class TestForgotPasswordInstitution(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.auth_user = AuthUserFactory()
        self.get_url = web_url_for('redirect_unsupported_institution')
        self.post_url = web_url_for('forgot_password_institution_post')
        self.user.verification_key_v2 = {}
        self.user.save()


    # log users out before they land on institutional forgot password page
    def test_forgot_password_logs_out_user(self):
        # TODO: check in qa url encoding
        # visit forgot password link while another user is logged in
        res = self.app.get(self.get_url, auth=self.auth_user.auth)
        # check redirection to CAS logout
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert quote_plus('campaign=unsupportedinstitution') in location
        assert 'logout?service=' in location

    # test that institutional forgot password page redirects to CAS unsupported
    # institution page
    def test_get_forgot_password(self):
        res = self.app.get(self.get_url)
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'campaign=unsupportedinstitution' in location

    # test that user from disabled institution can receive reset password email
    def test_can_receive_reset_password_email(self):
        # submit email to institutional forgot-password page

        with capture_notifications() as notifications:
            res = self.app.post(self.post_url, data={'forgot_password-email': self.user.username})

        # check mail was sent
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_FORGOT_PASSWORD_INSTITUTION
        # check http 200 response
        assert res.status_code == 200
        # check request URL is /forgotpassword
        assert res.request.path == self.post_url
        # check push notification
        assert_in_html('If there is an OSF account', res.text)
        assert_not_in_html('Please wait', res.text)

        # check verification_key_v2 is set
        self.user.reload()
        assert self.user.verification_key_v2 != {}

    # test that non-existing user cannot receive reset password email
    def test_cannot_receive_reset_password_email(self):
        # load forgot password page and submit email

        with capture_notifications() as notifications:
            res = self.app.post(self.post_url, data={'forgot_password-email': 'fake' + self.user.username})
        # check mail was not sent
        assert notifications == {'emails': [], 'emits': []}

        # check http 200 response
        assert res.status_code == 200
        # check request URL is /forgotpassword-institution
        assert res.request.path == self.post_url
        # check push notification
        assert_in_html('If there is an OSF account', res.text)
        assert_not_in_html('Please wait', res.text)

        # check verification_key_v2 is not set
        self.user.reload()
        assert self.user.verification_key_v2 == {}

    # test that non-existing user cannot receive institutional reset password email
    def test_not_active_user_no_reset_password_email(self):
        self.user.deactivate_account()
        self.user.save()

        with capture_notifications() as notifications:
            res = self.app.post(self.post_url, data={'forgot_password-email': self.user.username})

        # check mail was not sent
        assert notifications == {'emails': [], 'emits': []}
        # check http 200 response
        assert res.status_code == 200
        # check request URL is /forgotpassword-institution
        assert res.request.path == self.post_url
        # check push notification
        assert_in_html('If there is an OSF account', res.text)
        assert_not_in_html('Please wait', res.text)

        # check verification_key_v2 is not set
        self.user.reload()
        assert self.user.verification_key_v2 == {}

    # test that user cannot submit forgot password request too quickly
    def test_cannot_reset_password_twice_quickly(self):
        # submit institutional forgot-password request in rapid succession
        res = self.app.post(self.post_url, data={'forgot_password-email': self.user.username})
        res = self.app.post(self.post_url, data={'forgot_password-email': self.user.username})

        # check http 200 response
        assert res.status_code == 200
        # check push notification
        assert_in_html('Please wait', res.text)
        assert_not_in_html('If there is an OSF account', res.text)

