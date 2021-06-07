import pytest

from osf_tests.factories import (
    OutcomeReportFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestOutcomeReportList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def payload(self, node):
        return {
            'data': {
                'type': 'outcome_report',
                'attributes': {
                    'title': 'new title'
                },
                'relationships': {
                    'node': {
                        'data': {
                            'type': 'nodes',
                            'id': node._id
                        }
                    }
                }
            }
        }

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
    def outcome_report_deleted(self, node, schema):
        return OutcomeReportFactory(deleted=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def url(self, outcome_report):
        return '/v2/outcome_reports/'

    def test_outcome_report_list(self, app, outcome_report, outcome_report_public, outcome_report_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 1
        assert outcome_report_public._id == data[0]['id']

    def test_outcome_report_create(self, app, node, user, payload, url):
        resp = app.post_json_api(url, payload,  auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 1
