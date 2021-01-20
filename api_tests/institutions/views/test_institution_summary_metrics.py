import pytest
import datetime

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory
)
from osf.metrics import InstitutionProjectCounts


@pytest.mark.es
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
