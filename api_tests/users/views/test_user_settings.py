# -*- coding: utf-8 -*-
import mock
import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
)

@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.mark.django_db
class TestUserRequestExport:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/export/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-account-export-form',
                'attributes': {}
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post(self, mock_mail, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.email_last_sent is not None
        assert mock_mail.call_count == 1

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post_invalid_type(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        user_one.reload()
        assert user_one.email_last_sent is None
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_exceed_throttle(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429


@pytest.mark.django_db
class TestUserRequestDeactivate:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/deactivate/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-account-deactivate-form',
                'attributes': {}
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post(self, mock_mail, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        assert user_one.email_last_sent is None
        assert user_one.requested_deactivation is False
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.email_last_sent is not None
        assert user_one.requested_deactivation is True
        assert mock_mail.call_count == 1

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post_invalid_type(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        user_one.reload()
        assert user_one.email_last_sent is None
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_exceed_throttle(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429
