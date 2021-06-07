import pytest

from osf_tests.factories import (
    OutcomeReportFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestOutcomeReportDetail:

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
    def outcome_report_deleted(self, node, schema):
        return OutcomeReportFactory(deleted=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def url(self, outcome_report):
        return f'/v2/outcome_reports/{outcome_report._id}/'

    def test_outcome_report_detail(self, app, outcome_report, outcome_report_public, outcome_report_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == outcome_report._id
        assert data == {
            'attributes': {
                'deleted': None,
                'public': None,
                'responses': {},
                'title': None
            },
            'id': outcome_report._id,
            'links': {
                'self': f'http://localhost:8000/v2/outcome_reports/{outcome_report._id}/'
            },
            'relationships': {
                'node': {
                    'data': {
                        'id': outcome_report.node._id,
                        'type': 'nodes'
                    },
                    'links': {
                        'related': {
                            'href': f'http://localhost:8000/v2/nodes/{outcome_report.node._id}/',
                            'meta': {}
                        }
                    }
                },
                'schema': {
                    'data': {
                        'id': outcome_report.schema._id,
                        'type': 'registration-schemas'
                    },
                    'links': {
                        'related': {
                            'href': f'http://localhost:8000/v2/schemas/registrations/{outcome_report.schema._id}/',
                            'meta': {}
                        }
                    }
                },
                'versions': {
                    'links': {
                        'related': {
                            'href': f'http://localhost:8000/v2/outcome_reports/{outcome_report._id}/versions/',
                            'meta': {}
                        }
                    }
                }
            },
            'type': 'outcome_report'
        }