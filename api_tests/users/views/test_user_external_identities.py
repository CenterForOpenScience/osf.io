# -*- coding: utf-8 -*-
import pytest

from osf_tests.factories import AuthUserFactory
from api.base.settings.defaults import API_BASE


@pytest.fixture()
def user():
    user = AuthUserFactory()
    user.external_identity = {
        'ORCID': {
            '0000-0001-9143-4653': 'VERIFIED'
        },
        'LOTUS': {
            '0000-0001-9143-4652': 'LINK'
        }
    }
    user.save()
    return user


@pytest.mark.django_db
class TestUserIdentitiesList:

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/settings/identities/'.format(API_BASE, user._id)

    def test_authorized_gets_200(self, app, user, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'] == {
            'ORCID': {
                '0000-0001-9143-4653': 'VERIFIED'
            },
            'LOTUS': {
                '0000-0001-9143-4652': 'LINK'
            }
        }

    def test_anonymous_gets_401(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'


@pytest.mark.django_db
class TestUserIdentitiesDetail:

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/settings/identities/ORCID/'.format(API_BASE, user._id)

    def test_authorized_gets_200(self, app, user, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'] == {'ORCID': {'0000-0001-9143-4653': 'VERIFIED'}}

    def test_anonymous_gets_401(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_authorized_delete_204(self, app, user, url):
        res = app.delete(url, auth=user.auth)
        assert res.status_code == 204

        user.refresh_from_db()
        assert user.external_identity == {
            'LOTUS': {
                '0000-0001-9143-4652': 'LINK'
            }
        }
