import json

import jwe
import jwt
import pytest

from api.base import settings
from api.base.settings.defaults import API_BASE

from framework.auth import signals, Auth

from osf.models import OSFUser
from osf_tests.factories import InstitutionFactory, ProjectFactory, UserFactory

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

    return jwe.encrypt(
        jwt.encode(
            {
                'sub': username,
                'data': json.dumps(data)
            },
            settings.JWT_SECRET,
            algorithm='HS256'
        ),
        settings.JWE_SECRET
    )


@pytest.mark.django_db
class TestInstitutionAuth:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url_auth_institution(self):
        return '/{0}institutions/auth/'.format(API_BASE)

    def test_invalid_payload(self, app, url_auth_institution):
        res = app.post(url_auth_institution, 'INVALID_PAYLOAD', expect_errors=True)
        assert res.status_code == 403

    def test_new_user_created(self, app, url_auth_institution, institution):

        username = 'user_created@osf.edu'
        assert OSFUser.objects.filter(username=username).count() == 0

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        assert user.accepted_terms_of_service is not None
        assert institution in user.affiliated_institutions.all()

    def test_existing_user_found_but_not_affiliated(self, app, institution, url_auth_institution):

        username = 'user_not_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert institution in user.affiliated_institutions.all()

    def test_user_found_and_affiliated(self, app, institution, url_auth_institution):

        username = 'user_affiliated@osf.edu'
        user = make_user(username, 'Foo Bar')
        user.affiliated_institutions.add(institution)
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user.reload()
        assert user.fullname == 'Foo Bar'
        assert user.affiliated_institutions.count() == 1

    def test_new_user_names_guessed_if_not_provided(self, app, institution, url_auth_institution):

        username = 'user_created_with_fullname_only@osf.edu'
        res = app.post(url_auth_institution, make_payload(institution, username))
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        # Given name and family name are guessed from full name
        assert user.given_name == 'Fake'
        assert user.family_name == 'User'

    def test_new_user_names_used_when_provided(self, app, institution, url_auth_institution):

        username = 'user_created_with_names@osf.edu'
        res = app.post(
            url_auth_institution,
            make_payload(institution, username, given_name='Foo', family_name='Bar')
        )
        assert res.status_code == 204

        user = OSFUser.objects.filter(username=username).first()
        assert user
        assert user.fullname == 'Fake User'
        # Given name and family name are set instead of guessed
        assert user.given_name == 'Foo'
        assert user.family_name == 'Bar'

    def test_user_active(self, app, institution, url_auth_institution):

        username, fullname, password = 'user_active@user.edu', 'Foo Bar', 'FuAsKeEr'
        user = make_user(username, fullname)
        user.set_password(password)
        user.save()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User'
                )
            )
        assert res.status_code == 204
        assert not mock_signals.signals_sent()

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User names remains untouched
        assert user.fullname == fullname
        assert user.family_name == 'Bar'
        assert user.given_name == 'Foo'
        # Existing active user keeps their password
        assert user.has_usable_password()
        assert user.check_password(password)
        # Confirm affiliation
        assert institution in user.affiliated_institutions.all()

    def test_user_unclaimed(self, app, institution, url_auth_institution):

        username, fullname = 'user_nclaimed@user.edu', 'Foo Bar'
        project = ProjectFactory()
        user = project.add_unregistered_contributor(
            fullname=fullname,
            email=username,
            auth=Auth(project.creator)
        )
        user.save()
        # Unclaimed user is given an unusable password when being added as a contributor
        assert not user.has_usable_password()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User'
                )
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User becomes active and all names are updated
        assert user.is_active
        assert user.fullname == 'Fake User'
        assert user.family_name == 'User'
        assert user.given_name == 'Fake'
        # Unclaimed records must have been cleared
        assert not user.unclaimed_records
        # Previously unclaimed user must be assigned a usable password during institution auth
        assert user.has_usable_password()
        # User remains to be a contributor of the project
        assert project.is_contributor(user)
        # Confirm affiliation
        assert institution in user.affiliated_institutions.all()

    def test_user_unconfirmed(self, app, institution, url_auth_institution):

        username, fullname, password = 'user_unconfirmed@osf.edu', 'Foo Bar', 'FuAsKeEr'
        user = OSFUser.create_unconfirmed(username, password, fullname)
        user.save()
        # Unconfirmed user has a usable password created during sign-up
        assert user.has_usable_password()

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User'
                )
            )
        assert res.status_code == 204
        assert mock_signals.signals_sent() == set([signals.user_confirmed])

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # User becomes active and all names are updated
        assert user.is_active
        assert user.fullname == 'Fake User'
        assert user.family_name == 'User'
        assert user.given_name == 'Fake'
        # Pending email verifications must be cleared
        assert not user.email_verifications
        # Previously unconfirmed user must be given a new password during institution auth
        assert user.has_usable_password()
        assert not user.check_password(password)
        # Confirm affiliation
        assert institution in user.affiliated_institutions.all()

    def test_user_inactive(self, app, institution, url_auth_institution):

        username, fullname, password = 'user_inactive@osf.edu', 'Foo Bar', 'FuAsKeEr'
        user = make_user(username, fullname)
        user.set_password(password)
        # User must be saved before deactivation
        user.save()
        user.disable_account()
        user.save()
        # Disabled user still has the original usable password
        assert user.has_usable_password()
        assert user.check_password(password)

        with capture_signals() as mock_signals:
            res = app.post(
                url_auth_institution,
                make_payload(
                    institution,
                    username,
                    family_name='User',
                    given_name='Fake',
                    fullname='Fake User'
                ),
                expect_errors=True
            )
        assert res.status_code == 403
        assert not mock_signals.signals_sent()

        user = OSFUser.objects.filter(username=username).first()
        assert user
        # Inactive user remains untouched, including affiliation
        assert user.is_disabled
        assert user.fullname == fullname
        assert user.given_name == 'Foo'
        assert user.family_name == 'Bar'
        assert institution not in user.affiliated_institutions.all()
