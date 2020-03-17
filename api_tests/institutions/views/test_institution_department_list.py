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

    def test_get(self, app, url, user, user2, admin, institution):

        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(url, auth=admin.auth, expect_errors=True)
        assert resp.status_code == 200

        assert resp.json['data'] == []

        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'Offense'
        user_counts.save()
        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'Defense'
        user_counts.save()

        user_counts = UserInstitutionProjectCounts.record_user_institution_project_counts(
            user=user2,
            institution=institution,
            public_project_count=1,
            private_project_count=1
        )
        user_counts.department = 'Offense'
        user_counts.save()

        import time
        time.sleep(2)  # ES is slow

        resp = app.get(url, auth=admin.auth, expect_errors=True)
        assert resp.status_code == 200
        assert resp.json['data'] == [
            {'id': '',
             'type': 'institution-departments',
             'attributes': {
                 'name': 'Offense', 'number_of_users': 2
             },
             'links': {}
             },
            {'id': '',
             'type': 'institution-departments',
             'attributes': {
                 'name': 'Defense',
                 'number_of_users': 0
             },
             'links': {}
             }
        ]

        resp = app.get(f'{url}?filter[name]=Offense', auth=admin.auth, expect_errors=True)
        assert resp.status_code == 200
        assert resp.json['data'] == [
            {'id': '',
             'type': 'institution-departments',
             'attributes': {
                 'name': 'Offense', 'number_of_users': 2
             },
             'links': {}
             }
        ]
