import pytest
import datetime

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)
from osf.metrics import UserInstitutionProjectCounts


@pytest.mark.es
@pytest.mark.django_db
class TestInstitutionDepartmentList:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user2(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user3(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user4(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self, institution):
        user = AuthUserFactory()
        group = institution.get_group('institutional_admins')
        group.user_set.add(user)
        group.save()
        return user

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/departments/'

    def test_get(self, app, url, user, user2, user3, user4, admin, institution):

        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(url, auth=admin.auth)
        assert resp.status_code == 200

        assert resp.json['data'] == []

        # This represents a Department that had a user, but no longer has any users, so does not appear in results.
        UserInstitutionProjectCounts.record(
            user_id=user._id,
            institution_id=institution._id,
            department='Old Department',
            public_project_count=1,
            private_project_count=1,
            timestamp=datetime.date(2017, 2, 4)
        ).save()

        # The user has left the department
        UserInstitutionProjectCounts.record(
            user_id=user._id,
            institution_id=institution._id,
            department='New Department',
            public_project_count=1,
            private_project_count=1,
        ).save()

        # A second user entered the department
        UserInstitutionProjectCounts.record(
            user_id=user2._id,
            institution_id=institution._id,
            department='New Department',
            public_project_count=1,
            private_project_count=1
        ).save()

        # A new department with a single user to test sorting
        UserInstitutionProjectCounts.record(
            user_id=user3._id,
            institution_id=institution._id,
            department='Smaller Department',
            public_project_count=1,
            private_project_count=1
        ).save()

        # A user with no department
        UserInstitutionProjectCounts.record(
            user_id=user4._id,
            institution_id=institution._id,
            public_project_count=1,
            private_project_count=1
        ).save()

        import time
        time.sleep(2)  # ES is slow

        resp = app.get(url, auth=admin.auth)

        assert resp.json['data'] == [{
            'id': institution._id,
            'type': 'institution-departments',
            'attributes': {
                'name': 'New Department',
                'number_of_users': 2
            },
            'links': {'self': f'http://localhost:8000/v2/institutions/{institution._id}/departments/'}
        }, {
            'id': institution._id,
            'type': 'institution-departments',
            'attributes': {
                'name': 'Smaller Department',
                'number_of_users': 1
            },
            'links': {'self': f'http://localhost:8000/v2/institutions/{institution._id}/departments/'}
        }, {
            'id': institution._id,
            'type': 'institution-departments',
            'attributes': {
                'name': 'N/A',
                'number_of_users': 1
            },
            'links': {'self': f'http://localhost:8000/v2/institutions/{institution._id}/departments/'}
        }]

        resp = app.get(f'{url}?filter[name]=New Department', auth=admin.auth)

        assert resp.json['data'] == [{
            'id': institution._id,
            'type': 'institution-departments',
            'attributes': {
                'name': 'New Department',
                'number_of_users': 2
            },
            'links': {'self': f'http://localhost:8000/v2/institutions/{institution._id}/departments/'}
        }]
