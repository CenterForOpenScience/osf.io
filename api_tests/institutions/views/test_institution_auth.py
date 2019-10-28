import json

import jwe
import jwt
import pytest
from flask import Flask

from api.base import settings
from api.base.settings.defaults import API_BASE
from framework.auth import signals, Auth
from osf.models import OSFUser
from osf_tests.factories import InstitutionFactory, ProjectFactory, UserFactory

from tests.base import capture_signals

decoratorapp = Flask('decorators')


def make_user(username, fullname):
    return UserFactory(username=username, fullname=fullname)


def make_payload(
        institution, username, fullname='Fake User',
        given_name='', family_name=''
):
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

    @pytest.yield_fixture(autouse=True)
    def flask_request_context(self):
        """
        required for waffle cookies
        """
        with decoratorapp.test_request_context():
            yield

    @pytest.fixture()
    def url_auth_institution(self):
        return '/{0}institutions/auth/'.format(API_BASE)

    def test_creates_user(self, app, url_auth_institution, institution):
        username = 'hmoco@circle.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(institution, username)
            )

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
            res = app.post(
                url_auth_institution,
                make_payload(institution, username)
            )

        assert res.status_code == 204
        assert mock_signals.signals_sent() == set()

        user.reload()
        assert institution in user.affiliated_institutions.all()

    def test_finds_user(self, app, institution, url_auth_institution):
        username = 'hmoco@circle.edu'

        user = make_user(username, 'Mr Moco')
        user.affiliated_institutions.add(institution)
        user.save()

        res = app.post(
            url_auth_institution,
            make_payload(institution, username)
        )
        assert res.status_code == 204

        user.reload()
        assert user.affiliated_institutions.count() == 1

    def test_bad_token(self, app, url_auth_institution):
        res = app.post(
            url_auth_institution,
            'al;kjasdfljadf',
            expect_errors=True
        )
        assert res.status_code == 403

    def test_user_names_guessed_if_not_provided(
            self, app, institution, url_auth_institution):
        # Regression for https://openscience.atlassian.net/browse/OSF-7212
        username = 'fake@user.edu'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username)
        )

        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()

        assert user
        assert user.fullname == 'Fake User'
        assert user.given_name == 'Fake'
        assert user.family_name == 'User'

    def test_user_names_used_when_provided(
            self, app, institution, url_auth_institution):
        # Regression for https://openscience.atlassian.net/browse/OSF-7212
        username = 'fake@user.edu'
        res = app.post(
            url_auth_institution,
            make_payload(
                institution,
                username,
                family_name='West',
                given_name='Kanye'
            )
        )

        assert res.status_code == 204
        user = OSFUser.objects.filter(username=username).first()

        assert user
        assert user.fullname == 'Fake User'
        assert user.given_name == 'Kanye'
        assert user.family_name == 'West'

    def test_user_active(self, app, institution, url_auth_institution):

        username, fullname, password = 'fake_active@user.edu', 'Active User', 'FuAsKeEr'
        user = make_user(username, fullname)
        user.set_password(password)
        user.save()

        res = app.post(
            url_auth_institution,
            make_payload(
                institution,
                username,
                family_name='Family',
                given_name='Given',
                fullname='Full'
            )
        )
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User names remains untouched
        assert user.fullname == fullname
        assert user.family_name == 'User'
        assert user.given_name == 'Active'
        # Existing active user keeps their password
        assert user.has_usable_password()
        assert user.check_password(password)

    def test_user_unclaimed(self, app, institution, url_auth_institution):

        username, fullname = 'fake_unclaimed@user.edu', 'Unclaimed User'
        project = ProjectFactory()
        user = project.add_unregistered_contributor(
            fullname=fullname,
            email=username,
            auth=Auth(project.creator)
        )
        user.save()
        # Unclaimed user is given an unusable password when being added as a contributor
        assert not user.has_usable_password()

        res = app.post(
            url_auth_institution,
            make_payload(
                institution,
                username,
                family_name='Family',
                given_name='Given',
                fullname='Full'
            )
        )
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User becomes active and names (except the full name) are updated
        assert user.is_active
        assert user.fullname == 'Full'
        assert user.family_name == 'Family'
        assert user.given_name == 'Given'
        # Unclaimed records must have been cleared
        assert not user.unclaimed_records
        # Previously unclaimed user must be assigned a usable password during institution auth
        assert user.has_usable_password()
        # User remains to be a contributor of the project
        assert project.is_contributor(user)

    def test_user_unconfirmed(self, app, institution, url_auth_institution):

        username, fullname, password = 'fake_unconfirmed@user.edu', 'Unconfirmed User', 'FuAsKeEr'
        user = OSFUser.create_unconfirmed(username, password, fullname)
        user.save()
        # Unconfirmed user has a usable password created during sign-up
        assert user.has_usable_password()

        res = app.post(
            url_auth_institution,
            make_payload(
                institution,
                username,
                family_name='Family',
                given_name='Given',
                fullname='Full'
            )
        )
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User becomes active and names (except the full name) are updated
        assert user.is_active
        assert user.fullname == 'Full'
        assert user.family_name == 'Family'
        assert user.given_name == 'Given'
        # Pending email verifications must be cleared
        assert not user.email_verifications
        # Previously unconfirmed user must be given a new password during institution auth
        assert user.has_usable_password()
        assert not user.check_password(password)

    def test_user_inactive(self, app, institution, url_auth_institution):

        username, fullname, password = 'fake_inactive@user.edu', 'Inactive User', 'FuAsKeEr'
        user = make_user(username, fullname)
        user.set_password(password)
        # User must be saved before deactivation
        user.save()
        user.disable_account()
        user.save()
        # Disabled user still has the original usable password
        assert user.has_usable_password()
        assert user.check_password(password)

        res = app.post(
            url_auth_institution,
            make_payload(
                institution,
                username,
                family_name='Family',
                given_name='Given',
                fullname='Full'
            ),
            expect_errors=True
        )
        assert res.status_code == 403

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # Inactive user remains untouched
        assert user.is_disabled
        assert user.fullname == fullname
        assert user.family_name == 'User'
        assert user.given_name == 'Inactive'
