import pytest

from rest_framework import status

from api.base.settings.defaults import API_BASE
from api_tests.cas.util import fake, make_payload_login_institution

from framework.auth import signals

from osf_tests.factories import InstitutionFactory, UserFactory

from osf.models import OSFUser

from tests.base import capture_signals

# TODO 0: add tests for JWE/JWT failure and malformed request


@pytest.mark.django_db
class TestLoginInstitution(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/login/institution/'.format(API_BASE)

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def invalid_institution_id(self):
        return 'abc123'

    @pytest.fixture()
    def email(self):
        return fake.email()

    @pytest.fixture()
    def fullname(self):
        return fake.name()

    # test that first time institution login with new user creates the user confirmed and affiliated and returns 204
    def test_new_user_created(self, app, endpoint_url, institution, email, fullname):

        assert OSFUser.objects.filter(username=email).count() == 0

        payload = make_payload_login_institution(institution._id, username=email, fullname=fullname)
        with capture_signals() as mock_signals:
            res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        try:
            user = OSFUser.objects.filter(username=email).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert institution in user.affiliated_institutions.all()

    # test that first time institution login with existing user affiliates the user and returns 204
    def test_existing_user_affiliated(self, app, endpoint_url, user, institution):

        assert user.affiliated_institutions.count() == 0

        payload = make_payload_login_institution(institution._id, username=user.username, fullname=user.fullname)
        res = app.post(endpoint_url, payload)
        user.reload()

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert institution in user.affiliated_institutions.all()
        assert user.affiliated_institutions.count() == 1

    # test that institution login with existing affiliated user should return 204
    def test_affiliated_user(self, app, endpoint_url, user, institution):

        user.affiliated_institutions.add(institution)
        user.reload()
        assert user.affiliated_institutions.count() == 1

        payload = make_payload_login_institution(institution._id, username=user.username, fullname=user.fullname)
        res = app.post(endpoint_url, payload)

        assert res.status_code == 204

    # test that institution login with invalid institution id should raise 401
    def test_invalid_institution_id(self, app, endpoint_url, invalid_institution_id, email, fullname):

        assert OSFUser.objects.filter(username=email).count() == 0

        payload = make_payload_login_institution(invalid_institution_id, username=email, fullname=fullname)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40107

    # test that institution login without username should raise 401
    def test_missing_username(self, app, endpoint_url, institution, fullname):

        payload = make_payload_login_institution(institution._id, fullname=fullname)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40107

    # test that institution login without names should raise 401
    def test_missing_name(self, app, endpoint_url, institution, email):

        payload = make_payload_login_institution(institution._id, username=email)
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40107

    # test that institution login with only fullname should guess given name and family name
    def test_user_names_guessed_if_not_provided(self, app, endpoint_url, institution, email):

        given_name = 'User0001'
        family_name = 'Test'
        fullname = '{} {}'.format(given_name, family_name)

        payload = make_payload_login_institution(
            institution_id=institution._id,
            username=email,
            fullname=fullname
        )
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT

        try:
            user = OSFUser.objects.filter(username=email).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert user.fullname == fullname
        assert user.given_name == given_name
        assert user.family_name == family_name

    # test that institution login with given name and family name should override guessed names
    def test_user_names_used_when_provided(self, app, endpoint_url, institution, email, fullname):

        given_name = 'User0001'
        family_name = 'Test'

        payload = make_payload_login_institution(
            institution_id=institution._id,
            username=email,
            fullname=fullname,
            given_name=given_name,
            family_name=family_name
        )
        res = app.post(endpoint_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT

        try:
            user = OSFUser.objects.filter(username=email).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert user.fullname == fullname
        assert user.given_name == given_name
        assert user.family_name == family_name
