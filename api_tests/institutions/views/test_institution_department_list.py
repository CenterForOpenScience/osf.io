import pytest
import datetime

from api.base.settings.defaults import API_BASE, DEFAULT_ES_NULL_VALUE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)
from osf.metrics.reports import InstitutionalUserReport
from osf.metrics.utils import YearMonth


@pytest.mark.es_metrics
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
    def populate_counts(self, user, user2, user3, user4, admin, institution):
        # This represents a Department that had a user, but no longer has any users, so does not appear in results.
        InstitutionalUserReport(
            report_yearmonth=YearMonth(2017, 2),
            user_id=user._id,
            institution_id=institution._id,
            department_name='Old Department',
            public_project_count=1,
            private_project_count=1,
        ).save(refresh=True)

        _this_month = YearMonth.from_date(datetime.date.today())

        # The user has left the department
        InstitutionalUserReport(
            report_yearmonth=_this_month,
            user_id=user._id,
            institution_id=institution._id,
            department_name='New Department',
            public_project_count=1,
            private_project_count=1,
        ).save(refresh=True)

        # A second user entered the department
        InstitutionalUserReport(
            report_yearmonth=_this_month,
            user_id=user2._id,
            institution_id=institution._id,
            department_name='New Department',
            public_project_count=1,
            private_project_count=1,
        ).save(refresh=True)

        # A new department with a single user to test sorting
        InstitutionalUserReport(
            report_yearmonth=_this_month,
            user_id=user3._id,
            institution_id=institution._id,
            department_name='Smaller Department',
            public_project_count=1,
            private_project_count=1,
        ).save(refresh=True)

        # A user with no department
        InstitutionalUserReport(
            report_yearmonth=_this_month,
            user_id=user4._id,
            institution_id=institution._id,
            public_project_count=1,
            private_project_count=1,
        ).save(refresh=True)

    @pytest.fixture()
    def admin(self, institution):
        user = AuthUserFactory()
        group = institution.get_group('institutional_admins')
        group.user_set.add(user)
        group.save()
        return user

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/metrics/departments/'

    def test_auth(self, app, url, user, admin):

        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(url, auth=admin.auth)
        assert resp.status_code == 200

        assert resp.json['data'] == []

    def test_get(self, app, url, admin, institution, populate_counts):
        resp = app.get(url, auth=admin.auth)

        assert resp.json['data'] == [{
            'id': f'{institution._id}-New-Department',
            'type': 'institution-departments',
            'attributes': {
                'name': 'New Department',
                'number_of_users': 2
            },
            'links': {},
        }, {
            'id': f'{institution._id}-{DEFAULT_ES_NULL_VALUE}',
            'type': 'institution-departments',
            'attributes': {
                'name': DEFAULT_ES_NULL_VALUE,
                'number_of_users': 1
            },
            'links': {},
        }, {
            'id': f'{institution._id}-Smaller-Department',
            'type': 'institution-departments',
            'attributes': {
                'name': 'Smaller Department',
                'number_of_users': 1
            },
            'links': {},
        }]

        # Tests CSV Export
        headers = {
            'accept': 'text/csv'
        }
        resp = app.get(url, auth=admin.auth, headers=headers)

        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8'
        response_body = resp.text
        rows = response_body.split('\r\n')
        header_row = rows[0].split(',')
        new_department_row = rows[1].split(',')
        na_row = rows[2].split(',')
        smaller_department_row = rows[3].split(',')

        assert header_row == ['name', 'number_of_users']
        assert new_department_row == ['New Department', '2']
        assert smaller_department_row == ['Smaller Department', '1']
        assert na_row == ['N/A', '1']
