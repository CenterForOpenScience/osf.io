import pytest
from datetime import timedelta

from osf_tests.factories import (
    OutcomeReportFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestOutcomeReportVersions:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def outcome_report(self, node, schema):
        return OutcomeReportFactory(node=node, schema=schema)

    @pytest.fixture()
    def outcome_report_public(self, node, schema):
        return OutcomeReportFactory(public=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def outcome_report_version(self, node, schema):
        """
        Version that's a day old.
        """
        return OutcomeReportFactory(public=timezone.now() - timedelta(days=1), node=node, schema=schema)

    @pytest.fixture()
    def url(self, outcome_report):
        return f'/v2/outcome_reports/{outcome_report._id}/versions/'

    def test_outcome_report_versions(self, app, outcome_report, outcome_report_public, outcome_report_version, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        assert outcome_report_public._id == data[0]['id']
        assert outcome_report_version._id == data[1]['id']
