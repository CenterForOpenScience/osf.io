import pytest
import datetime

from waffle.testutils import override_flag
from osf.metrics import InstitutionProjectCounts

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)
from osf.metrics.reports import InstitutionMonthlySummaryReport
from osf import features


@pytest.mark.es_metrics
@pytest.mark.django_db
class TestInstitutionSummaryMetrics:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
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
        return f'/{API_BASE}institutions/{institution._id}/metrics/summary/'

    def test_get(self, app, url, institution, user, admin):
        # Tests unauthenticated user
        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        # Tests unauthorized user
        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        # Record latest institutional metrics to ES
        public_project_count_latest = 24
        private_project_count_latest = 26
        institution_user_count_latest = 9
        timestamp_latest = datetime.datetime.now()

        # Uses record to specify user_count
        InstitutionProjectCounts.record(
            institution_id=institution._id,
            user_count=institution_user_count_latest,
            public_project_count=public_project_count_latest,
            private_project_count=private_project_count_latest,
            timestamp=timestamp_latest
        ).save()

        # Record earlier institutional metrics to ES
        public_project_count_early = 20
        private_project_count_early = 18
        institution_user_count_early = 4
        timestamp_early = timestamp_latest - datetime.timedelta(days=1)

        # Uses record to specify user_count
        InstitutionProjectCounts.record(
            institution_id=institution._id,
            user_count=institution_user_count_early,
            public_project_count=public_project_count_early,
            private_project_count=private_project_count_early,
            timestamp=timestamp_early
        ).save()

        import time
        time.sleep(5)

        # Tests authorized user with institution with metrics
        resp = app.get(url, auth=admin.auth)
        assert resp.status_code == 200

        # Validates the summary metrics returned by the API
        assert resp.json['data'] == {
            'id': institution._id,
            'type': 'institution-summary-metrics',
            'attributes': {
                'public_project_count': public_project_count_latest,
                'private_project_count': private_project_count_latest,
                'user_count': institution_user_count_latest
            },
            'links': {
                'self': f'http://localhost:8000/v2/institutions/{institution._id}/metrics/summary/'
            }
        }


@pytest.mark.es_metrics
@pytest.mark.django_db
class TestNewInstitutionSummaryMetricsList:
    @pytest.fixture(autouse=True)
    def _waffled(self):
        with override_flag(features.INSTITUTIONAL_DASHBOARD_2024, active=True):
            yield

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def rando(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institutional_admin(self, institution):
        admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    @pytest.fixture()
    def unshown_reports(self, institution):
        # Reports that should not be shown in the results
        # Report from another institution
        another_institution = InstitutionFactory()
        _summary_report_factory('2024-08', another_institution)
        # Old report from the same institution
        _summary_report_factory('2024-07', institution)
        _summary_report_factory('2018-02', institution)

    @pytest.fixture()
    def reports(self, institution):
        return [
            _summary_report_factory(
                '2024-08', institution,
                user_count=100,
                public_project_count=50,
                private_project_count=25,
                public_registration_count=10,
                embargoed_registration_count=5,
                published_preprint_count=15,
                public_file_count=20,
                storage_byte_count=5000000000,
                monthly_logged_in_user_count=80,
                monthly_active_user_count=60,
            ),
            _summary_report_factory(
                '2024-08', institution,
                user_count=200,
                public_project_count=150,
                private_project_count=125,
                public_registration_count=110,
                embargoed_registration_count=105,
                published_preprint_count=115,
                public_file_count=120,
                storage_byte_count=15000000000,
                monthly_logged_in_user_count=180,
                monthly_active_user_count=160,
            ),
        ]

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/metrics/summary/'

    def test_anon(self, app, url):
        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

    def test_rando(self, app, url, rando):
        resp = app.get(url, auth=rando.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_get_empty(self, app, url, institutional_admin):
        resp = app.get(url, auth=institutional_admin.auth)
        assert resp.status_code == 200
        assert resp.json['meta'] == {'version': '2.0'}

    def test_get_report(self, app, url, institutional_admin, institution, reports, unshown_reports):
        resp = app.get(url, auth=institutional_admin.auth)
        assert resp.status_code == 200

        data = resp.json['data']

        assert data['id'] == institution._id
        assert data['type'] == 'institution-summary-metrics'

        attributes = data['attributes']
        assert attributes['report_yearmonth'] == '2024-08'
        assert attributes['user_count'] == 200
        assert attributes['public_project_count'] == 150
        assert attributes['private_project_count'] == 125
        assert attributes['public_registration_count'] == 110
        assert attributes['embargoed_registration_count'] == 105
        assert attributes['published_preprint_count'] == 115
        assert attributes['public_file_count'] == 120
        assert attributes['storage_byte_count'] == 15000000000
        assert attributes['monthly_logged_in_user_count'] == 180
        assert attributes['monthly_active_user_count'] == 160

    def test_get_report_with_multiple_months_and_institutions(
        self, app, url, institutional_admin, institution
    ):
        # Create reports for multiple months and institutions
        other_institution = InstitutionFactory()
        _summary_report_factory(
            '2024-09', institution,
            user_count=250,
            public_project_count=200,
            private_project_count=150,
            public_registration_count=120,
            embargoed_registration_count=110,
            published_preprint_count=130,
            public_file_count=140,
            storage_byte_count=20000000000,
            monthly_logged_in_user_count=220,
            monthly_active_user_count=200,
        )
        _summary_report_factory(
            '2024-08', institution,
            user_count=200,
            public_project_count=150,
            private_project_count=125,
            public_registration_count=110,
            embargoed_registration_count=105,
            published_preprint_count=115,
            public_file_count=120,
            storage_byte_count=15000000000,
            monthly_logged_in_user_count=180,
            monthly_active_user_count=160,
        )
        _summary_report_factory(
            '2024-09', other_institution,
            user_count=300,
            public_project_count=250,
            private_project_count=200,
            public_registration_count=180,
            embargoed_registration_count=170,
            published_preprint_count=190,
            public_file_count=210,
            storage_byte_count=25000000000,
            monthly_logged_in_user_count=270,
            monthly_active_user_count=260,
        )

        resp = app.get(url, auth=institutional_admin.auth)
        assert resp.status_code == 200

        data = resp.json['data']

        assert data['id'] == institution._id
        assert data['type'] == 'institution-summary-metrics'

        attributes = data['attributes']

        assert attributes['report_yearmonth'] == '2024-09'
        assert attributes['user_count'] == 250
        assert attributes['public_project_count'] == 200
        assert attributes['private_project_count'] == 150
        assert attributes['public_registration_count'] == 120
        assert attributes['embargoed_registration_count'] == 110
        assert attributes['published_preprint_count'] == 130
        assert attributes['public_file_count'] == 140
        assert attributes['storage_byte_count'] == 20000000000
        assert attributes['monthly_logged_in_user_count'] == 220
        assert attributes['monthly_active_user_count'] == 200

    def test_get_with_valid_report_dates(self, app, url, institution, institutional_admin):
        _summary_report_factory(
            '2024-08',
            institution,
            user_count=0,
        )
        _summary_report_factory(
            '2024-09',
            institution,
            user_count=999,

        )
        _summary_report_factory(
            '2018-02',
            institution,
            user_count=4133,
        )

        resp = app.get(f'{url}?report_yearmonth=2024-08', auth=institutional_admin.auth)
        assert resp.status_code == 200

        attributes = resp.json['data']['attributes']
        assert attributes['user_count'] == 0

        resp = app.get(f'{url}?report_yearmonth=2018-02', auth=institutional_admin.auth)
        assert resp.status_code == 200

        attributes = resp.json['data']['attributes']
        assert attributes['user_count'] == 4133

    def test_get_with_invalid_report_date(self, app, url, institution, institutional_admin):
        _summary_report_factory(
            '2024-08',
            institution,
            user_count=0,
        )
        _summary_report_factory(
            '2024-09',
            institution,
            user_count=999,
        )

        # Request with an invalid report_date format
        resp = app.get(f'{url}?report_yearmonth=invalid-date', auth=institutional_admin.auth)
        assert resp.status_code == 200

        # Verify it defaults to the most recent report data
        attributes = resp.json['data']['attributes']
        assert attributes['user_count'] == 999

    def test_get_without_report_date_uses_most_recent(self, app, url, institution, institutional_admin):
        _summary_report_factory(
            '2024-08',
            institution,
            user_count=0,
        )
        _summary_report_factory(
            '2024-09',
            institution,
            user_count=999,
        )

        resp = app.get(url, auth=institutional_admin.auth)
        assert resp.status_code == 200

        attributes = resp.json['data']['attributes']
        assert attributes['user_count'] == 999


def _summary_report_factory(yearmonth, institution, **kwargs):
    report = InstitutionMonthlySummaryReport(
        report_yearmonth=yearmonth,
        institution_id=institution._id,
        **kwargs,
    )
    report.save(refresh=True)
    return report
