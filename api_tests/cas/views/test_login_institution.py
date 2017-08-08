import pytest

from rest_framework import status

from api.base.settings.defaults import API_BASE
from api_tests.cas.util import make_payload_login_institution

from framework.auth import signals

from osf_tests.factories import InstitutionFactory, UserFactory

from osf.models import OSFUser

from tests.base import capture_signals


@pytest.mark.django_db
class TestLoginInstitution(object):

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def login_url(self):
        return '/{0}cas/login/institution/'.format(API_BASE)

    @pytest.fixture()
    def invalid_institution_id(self):
        return 'abc123'

    @pytest.fixture()
    def username_new_user(self):
        return 'testuser0001@cos.io'

    @pytest.fixture()
    def fullname_new_user(self):
        return 'User0001 Test'

    def test_new_user(self, app, institution, login_url, username_new_user, fullname_new_user):

        assert OSFUser.objects.filter(username=username_new_user).count() == 0

        payload_new_user = make_payload_login_institution(institution._id, username=username_new_user, fullname=fullname_new_user)
        with capture_signals() as mock_signals:
            res = app.post(login_url, payload_new_user)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        try:
            user = OSFUser.objects.filter(username=username_new_user).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert institution in user.affiliated_institutions.all()

    def test_existing_user(self, app, user, institution, login_url):

        assert OSFUser.objects.filter(username=user.username).count() == 1
        assert user.affiliated_institutions.count() == 0

        payload_existing_user = make_payload_login_institution(institution._id, username=user.username, fullname=user.fullname)
        with capture_signals() as mock_signals:
            res = app.post(login_url, payload_existing_user)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert mock_signals.signals_sent() == set()

        user.reload()
        assert institution in user.affiliated_institutions.all()
        assert user.affiliated_institutions.count() == 1

    def test_affiliated_user(self, app, user, institution, login_url):

        assert OSFUser.objects.filter(username=user.username).count() == 1
        user.affiliated_institutions.add(institution)
        user.reload()
        assert user.affiliated_institutions.count() == 1

        payload_existing_user = make_payload_login_institution(institution._id, username=user.username, fullname=user.fullname)
        with capture_signals() as mock_signals:
            res = app.post(login_url, payload_existing_user)

        assert res.status_code == 204
        assert mock_signals.signals_sent() == set()

    def test_invalid_institution_id(self, app, login_url, invalid_institution_id, username_new_user, fullname_new_user):

        assert OSFUser.objects.filter(username=username_new_user).count() == 0

        payload_new_user = make_payload_login_institution(invalid_institution_id, username=username_new_user, fullname=fullname_new_user)
        with capture_signals() as mock_signals:
            res = app.post(login_url, payload_new_user, expect_errors=True)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert (mock_signals.signals_sent() != set([signals.user_confirmed]))

        try:
            user = OSFUser.objects.filter(username=username_new_user).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is None

    def test_missing_username(self, app, institution, login_url, fullname_new_user):

        payload_new_user_no_username = make_payload_login_institution(institution._id, fullname=fullname_new_user)
        res = app.post(login_url, payload_new_user_no_username, expect_errors=True)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_name(self, app, institution, login_url, username_new_user):

        payload_new_user_no_name = make_payload_login_institution(institution._id, username=username_new_user)
        res = app.post(login_url, payload_new_user_no_name, expect_errors=True)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_bad_request_data(self, app, user, institution, login_url):

        payload = make_payload_login_institution(
            institution._id,
            username=user.username,
            fullname=user.fullname,
            bad_secret=True
        )
        res = app.post(login_url, payload, expect_errors=True)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_names_guessed_if_not_provided(self, app, login_url, institution, username_new_user, fullname_new_user):

        payload = make_payload_login_institution(
            institution_id=institution._id,
            username=username_new_user,
            fullname=fullname_new_user,
        )
        res = app.post(login_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        try:
            user = OSFUser.objects.filter(username=username_new_user).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert user.fullname == fullname_new_user
        assert user.given_name == 'User0001'
        assert user.family_name == 'Test'

    def test_user_names_used_when_provided(self, app, login_url, institution, username_new_user, fullname_new_user):

        payload = make_payload_login_institution(
            institution_id=institution._id,
            username=username_new_user,
            fullname=fullname_new_user,
            given_name='0001User',
            family_name='0001Test'
        )
        res = app.post(login_url, payload)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        try:
            user = OSFUser.objects.filter(username=username_new_user).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert user.fullname == fullname_new_user
        assert user.given_name == '0001User'
        assert user.family_name == '0001Test'
