import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)
from osf.metrics import UserInstitutionProjectCounts
from osf.models import Institution
from osf.permissions import INSTITUTION_ADMIN
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


@pytest.mark.es
@pytest.mark.django_db
class TestInstitutionDepartmentList:

    @pytest.fixture(autouse=True)
    def mock_permission(self):
        content_type_id = ContentType.objects.get_for_model(Institution).id
        Permission.objects.create(codename=INSTITUTION_ADMIN, content_type_id=content_type_id)

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
    def admin_permission(self):
        return Permission.objects.get(codename=INSTITUTION_ADMIN)

    @pytest.fixture()
    def admin(self, admin_permission, institution):
        user = AuthUserFactory()
        user.add_obj_perm(admin_permission, institution)
        return user

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/departments/'

    def test_get(self, app, url, user, user2, user3, user4, admin, institution):

        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(url, auth=admin.auth, expect_errors=True)
        assert resp.status_code == 200

        assert resp.json['data'] == []

        # This represents a Department that had a user, but no longer has any users, so does not appear in results.
        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'Old Department'
        user_counts.save()

        # The user has left the department
        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'New Department'
        user_counts.save()

        # A second user entered the department
        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user2,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'New Department'
        user_counts.save()

        # A new department with a single user to test sorting
        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user3,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'Smaller Department'
        user_counts.save()

        # A user with no department
        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user4,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.save()

        import time
        time.sleep(2)  # ES is slow

        resp = app.get(url, auth=admin.auth)
        assert resp.json['data'] == [
            {'name': 'New Department', 'number_of_users': 2},
            {'name': 'Smaller Department', 'number_of_users': 1},
            {'name': 'N/A', 'number_of_users': 1},
        ]

        resp = app.get(f'{url}?filter[name]=New Department', auth=admin.auth)
        assert resp.json['data'] == [
            {'name': 'New Department', 'number_of_users': 2}
        ]
