import pytest

from api.base.settings import BYPASS_THROTTLE_TOKEN
from api.base.settings.defaults import API_BASE
from osf.models import NotificationTypeEnum
from osf_tests.factories import (
    UserFactory,
    UnconfirmedUserFactory,
)
from tests.utils import capture_notifications
from website import language


def resend_payload(email):
    return {
        'data': {
            'type': 'user_resend_confirmation',
            'attributes': {
                'email': email,
            }
        }
    }


class TestResendConfirmation:

    @pytest.fixture()
    def unconfirmed_user(self):
        return UnconfirmedUserFactory()

    @pytest.fixture()
    def confirmed_user(self):
        return UserFactory()

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}users/resend_confirmation/'

    @pytest.fixture()
    def headers(self):
        # skip DRF throttle
        return {'X-THROTTLE-TOKEN': BYPASS_THROTTLE_TOKEN}

    def test_post(self, app, url, headers, unconfirmed_user):
        email = unconfirmed_user.username
        old_tokens = set(unconfirmed_user.email_verifications)
        assert unconfirmed_user.email_last_sent is None

        with capture_notifications() as notifications:
            res = app.post_json_api(url, resend_payload(email), headers=headers)
        assert res.status_code == 200
        assert res.json['kind'] == 'success'
        assert res.json['message'] == language.RESEND_CONFIRMATION_SUCCESS_STATUS_MESSAGE.format(email=email)

        assert len(notifications['emits']) == 1
        emit = notifications['emits'][0]
        assert emit['type'] == NotificationTypeEnum.USER_INITIAL_CONFIRM_EMAIL
        assert emit['kwargs']['destination_address'] == email

        # the link in the email carries a freshly generated token, and it was saved
        unconfirmed_user.reload()
        new_tokens = set(unconfirmed_user.email_verifications) - old_tokens
        assert len(new_tokens) == 1
        confirmation_url = emit['kwargs']['event_context']['confirmation_url']
        assert f'confirm/{unconfirmed_user._id}/{new_tokens.pop()}/' in confirmation_url
        assert unconfirmed_user.email_last_sent is not None

    def test_post_email_case_insensitive(self, app, url, headers, unconfirmed_user):
        with capture_notifications() as notifications:
            res = app.post_json_api(url, resend_payload(unconfirmed_user.username.upper()), headers=headers)
        assert res.status_code == 200
        assert res.json['kind'] == 'success'
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.USER_INITIAL_CONFIRM_EMAIL

    def test_post_already_confirmed(self, app, url, headers, confirmed_user):
        email = confirmed_user.username

        with capture_notifications(expect_none=True):
            res = app.post_json_api(url, resend_payload(email), expect_errors=True, headers=headers)
        assert res.status_code == 400
        assert res.json['kind'] == 'error'
        assert res.json['message'] == language.RESEND_CONFIRMATION_ALREADY_CONFIRMED_ERROR_MESSAGE.format(email=email)
        confirmed_user.reload()
        assert confirmed_user.email_last_sent is None

    def test_post_unknown_email(self, app, url, headers):
        # same response as for an existing account
        email = 'random@random.com'

        with capture_notifications(expect_none=True):
            res = app.post_json_api(url, resend_payload(email), headers=headers)
        assert res.status_code == 200
        assert res.json['kind'] == 'success'
        assert res.json['message'] == language.RESEND_CONFIRMATION_SUCCESS_STATUS_MESSAGE.format(email=email)

    def test_post_missing_email(self, app, url, headers):
        payload = {
            'data': {
                'type': 'user_resend_confirmation',
                'attributes': {
                }
            }
        }
        with capture_notifications(expect_none=True):
            res = app.post_json_api(url, payload, expect_errors=True, headers=headers)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/email'
        assert res.json['errors'][0]['detail'] == 'This field is required.'

    def test_post_blank_email(self, app, url, headers):
        with capture_notifications(expect_none=True):
            res = app.post_json_api(url, resend_payload(''), expect_errors=True, headers=headers)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/email'
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'
