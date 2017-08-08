import pytest
import json
import jwt
import jwe

from api.base import settings
from api.base.settings.defaults import API_BASE
from framework.auth import signals
from osf.models import OSFUser
from osf_tests.factories import (
    InstitutionFactory,
    UserFactory,
)
from tests.base import capture_signals

def make_user(username, fullname):
    return UserFactory(username=username, fullname=fullname)

def make_payload(institution, username, fullname='Fake User', given_name='', family_name=''):
    data = {
        'provider': {
            'id': institution._id,
            'user': {
                'middleNames': '',
                'familyName': family_name,
                'givenName': given_name,
                'fullname': fullname,
                'suffix': '',
                'username': username
            }
        }
    }
    return jwe.encrypt(jwt.encode({
        'sub': username,
        'data': json.dumps(data)
    }, settings.JWT_SECRET, algorithm='HS256'), settings.JWE_SECRET)

@pytest.mark.django_db
class TestInstitutionAuth:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url_auth_institution(self):
        return '/{0}institutions/auth/'.format(API_BASE)

    def test_creates_user(self, app, url_auth_institution, institution):
        username = 'hmoco@circle.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))

        assert res.status_code == 204
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        user = OSFUser.objects.filter(username=username).first()

        assert user
        assert institution in user.affiliated_institutions.all()

    def test_adds_institution(self, app, institution, url_auth_institution):
        username = 'hmoco@circle.edu'

        user = make_user(username, 'Mr Moco')
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))

        assert res.status_code == 204
        assert mock_signals.signals_sent() == set()

        user.reload()
        assert institution in user.affiliated_institutions.all()

    def test_finds_user(self, app, institution, url_auth_institution):
        username = 'hmoco@circle.edu'

        user = make_user(username, 'Mr Moco')
        user.affiliated_institutions.add(institution)
        user.save()

        res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204

        user.reload()
        assert user.affiliated_institutions.count() == 1

    def test_bad_token(self, app, url_auth_institution):
        res = app.post(url_auth_institution, 'al;kjasdfljadf', expect_errors=True)
        assert res.status_code == 403

    def test_user_names_guessed_if_not_provided(self, app, institution, url_auth_institution):
        # Regression for https://openscience.atlassian.net/browse/OSF-7212
        username = 'fake@user.edu'
        res = app.post(url_auth_institution, make_payload(institution, username))

        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()

        assert user
        assert user.fullname == 'Fake User'
        assert user.given_name == 'Fake'
        assert user.family_name == 'User'

    def test_user_names_used_when_provided(self, app, institution, url_auth_institution):
        # Regression for https://openscience.atlassian.net/browse/OSF-7212
        username = 'fake@user.edu'
        res = app.post(url_auth_institution, make_payload(institution, username, family_name='West', given_name='Kanye'))

        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()

        assert user
        assert user.fullname == 'Fake User'
        assert user.given_name == 'Kanye'
        assert user.family_name == 'West'
