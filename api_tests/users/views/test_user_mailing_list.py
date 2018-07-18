# -*- coding: utf-8 -*-
import pytest

from osf_tests.factories import AuthUserFactory
from api.base.settings.defaults import API_BASE
from website.settings import MAILCHIMP_GENERAL_LIST, OSF_HELP_LIST


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def unauthorized_user():
    return AuthUserFactory()


@pytest.fixture()
def url(user):
    return '/{}users/{}/settings/'.format(API_BASE, user._id)


@pytest.fixture()
def payload(user):
    return {
        'data': {
            'id': user._id,
            'type': 'user-settings',
            'attributes': {
                'subscribe_osf_help_email': False,
                'subscribe_osf_general_email': True
            }
        }
    }

@pytest.fixture()
def bad_payload(user):
    return {
        'data': {
            'id': user._id,
            'type': 'user-settings',
            'attributes': {
                'subscribe_osf_help_email': False,
                'subscribe_osf_general_email': '22',
            }
        }
    }


@pytest.mark.django_db
class TestGetUserMailingList:

    def test_authorized_gets_200(self, app, user, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        assert res.json['data']['attributes']['subscribe_osf_help_email'] is True
        assert res.json['data']['attributes']['subscribe_osf_general_email'] is False
        assert res.json['data']['type'] == 'user-settings'

    def test_anonymous_gets_401(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_unauthorized_gets_403(self, app, url, unauthorized_user):
        res = app.get(url, auth=unauthorized_user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.content_type == 'application/vnd.api+json'

    def test_post_405(self, app, url, user):
        res = app.post(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405
        assert res.content_type == 'application/vnd.api+json'

@pytest.mark.django_db
class TestPatchUserMailingList:

    def test_authorized_patch_200(self, app, user, payload, url):
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200

        user.refresh_from_db()
        assert user.osf_mailing_lists[OSF_HELP_LIST] is False
        assert user.osf_mailing_lists[MAILCHIMP_GENERAL_LIST] is True

    def test_bad_payload_patch_400(self, app, user, bad_payload, url):
        res = app.patch_json_api(url, bad_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == u'"22" is not a valid boolean.'

    def test_anonymous_patch_401(self, app, url, payload):
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_unauthorized_patch_403(self, app, url, payload, unauthorized_user):
        res = app.patch_json_api(url, payload, auth=unauthorized_user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.content_type == 'application/vnd.api+json'
