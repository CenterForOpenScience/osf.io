import pytest

from osf_tests.factories import (
    OutcomeReportFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestUserOutcomeReportList:

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def outcome_report(self, user, user_write, user_admin, node, schema):
        node.add_contributor(user, permissions='read')
        node.add_contributor(user_write, permissions='write')
        node.add_contributor(user_admin, permissions='admin')
        return OutcomeReportFactory(node=node, schema=schema)

    @pytest.fixture()
    def outcome_report_public(self, node, schema):
        return OutcomeReportFactory(public=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def outcome_report_deleted(self, node, schema):
        return OutcomeReportFactory(deleted=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def url(self, outcome_report):
        return f'/v2/outcome_reports/'

    def test_outcome_report_list(self, app, outcome_report, outcome_report_public, outcome_report_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 1
        assert outcome_report_public._id == data[0]['id']