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


@pytest.fixture()
def unauthorized_user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestUserIdentitiesList:

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/settings/identities/'.format(API_BASE, user._id)

    def test_authorized_gets_200(self, app, user, url):
        res = app.get(url, auth=user.auth)
        print res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['attributes'] == {u'status': u'LINK', u'external_id': u'0000-0001-9143-4652'}
        assert res.json['data'][0]['type'] == 'external-identities'
        assert res.json['data'][0]['id'] == 'LOTUS'

        assert res.json['data'][1]['attributes'] == {u'status': u'VERIFIED', u'external_id': u'0000-0001-9143-4653'}
        assert res.json['data'][1]['type'] == 'external-identities'
        assert res.json['data'][1]['id'] == 'ORCID'

    def test_anonymous_gets_401(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_unauthorized_gets_403(self, app, url, unauthorized_user):
        res = app.get(url, auth=unauthorized_user.auth, expect_errors=True)
        assert res.status_code == 403
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
        assert res.json['data'] == {
            u'attributes': {
                u'external_id': u'0000-0001-9143-4653',
                u'status': u'VERIFIED'
            },
            u'id': u'ORCID',
            u'links': {
                u'self': u'http://localhost:8000/v2/users/{}/settings/identities/ORCID/'.format(user._id)
            },
            u'type': u'external-identities'
        }

    def test_anonymous_gets_401(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_no_creds_delete_204(self, app, user, url):
        res = app.delete(url, auth=user.auth)
        assert res.status_code == 204

        user.refresh_from_db()
        assert user.external_identity == {
            'LOTUS': {
                '0000-0001-9143-4652': 'LINK'
            }
        }

    def test_unauthorized_delete_403(self, app, url, unauthorized_user):
        res = app.get(url, auth=unauthorized_user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.content_type == 'application/vnd.api+json'
