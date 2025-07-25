from osf.models import NotificationType
from tests.base import OsfTestCase
from osf_tests.factories import (
    UserFactory,
    UnconfirmedUserFactory,
)
from tests.utils import capture_notifications
from website.util import web_url_for
from tests.test_webtests import assert_in_html

class TestResendConfirmation(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.unconfirmed_user = UnconfirmedUserFactory()
        self.confirmed_user = UserFactory()
        self.get_url = web_url_for('resend_confirmation_get')
        self.post_url = web_url_for('resend_confirmation_post')

    # test that resend confirmation page is load correctly
    def test_resend_confirmation_get(self):
        res = self.app.get(self.get_url)
        assert res.status_code == 200
        assert 'Resend Confirmation' in res.text
        assert res.get_form('resendForm')

    # test that unconfirmed user can receive resend confirmation email
    def test_can_receive_resend_confirmation_email(self):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('resendForm')
        form['email'] = self.unconfirmed_user.unconfirmed_emails[0]
        with capture_notifications() as notifications:
            res = form.submit(self.app)
        # check email, request and response
        assert len(notifications) == 1
        assert notifications[0]['type'] == NotificationType.Type.USER_INITIAL_CONFIRM_EMAIL
        assert res.status_code == 200
        assert res.request.path == self.post_url
        assert_in_html('If there is an OSF account', res.text)


    # test that confirmed user cannot receive resend confirmation email
    def test_cannot_receive_resend_confirmation_email_1(self):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('resendForm')
        form['email'] = self.confirmed_user.emails.first().address
        with capture_notifications() as notifications:
            res = form.submit(self.app)

        assert not notifications
        assert res.status_code == 200
        assert res.request.path == self.post_url
        assert_in_html('has already been confirmed', res.text)

    # test that non-existing user cannot receive resend confirmation email
    def test_cannot_receive_resend_confirmation_email_2(self):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('resendForm')
        form['email'] = 'random@random.com'
        with capture_notifications() as notifications:
            res = form.submit(self.app)
        # check email, request and response
        assert notifications
        assert res.status_code == 200
        assert res.request.path == self.post_url
        assert_in_html('If there is an OSF account', res.text)

    # test that user cannot submit resend confirmation request too quickly
    def test_cannot_resend_confirmation_twice_quickly(self):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('resendForm')
        form['email'] = self.unconfirmed_user.email
        form.submit(self.app)
        res = form.submit(self.app)

        # check request and response
        assert res.status_code == 200
        assert_in_html('Please wait', res.text)

