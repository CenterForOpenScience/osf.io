import pytest

from osf_tests.factories import (
    SchemaResponseFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestSchemaResponseDetail:

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
    def schema_response(self, node, schema):
        return SchemaResponseFactory(node=node, schema=schema)

    @pytest.fixture()
    def schema_response_public(self, node, schema):
        return SchemaResponseFactory(public=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def schema_response_deleted(self, node, schema):
        return SchemaResponseFactory(deleted=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/schema_responses/{schema_response._id}/'

    def test_schema_response_detail(self, app, schema_response, schema_response_public, schema_response_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id
        assert data == {
            'attributes': {
                'deleted': None,
                'public': None,
                'responses': {},
                'title': None
            },
            'id': schema_response._id,
            'links': {
                'self': f'http://localhost:8000/v2/schema_response/{schema_response._id}/'
            },
            'relationships': {
                'node': {
                    'data': {
                        'id': schema_response.node._id,
                        'type': 'nodes'
                    },
                    'links': {
                        'related': {
                            'href': f'http://localhost:8000/v2/nodes/{schema_response.node._id}/',
                            'meta': {}
                        }
                    }
                },
                'schema': {
                    'data': {
                        'id': schema_response.schema._id,
                        'type': 'registration-schemas'
                    },
                    'links': {
                        'related': {
                            'href': f'http://localhost:8000/v2/schemas/registrations/{schema_response.schema._id}/',
                            'meta': {}
                        }
                    }
                },
                'versions': {
                    'links': {
                        'related': {
                            'href': f'http://localhost:8000/v2/schema_response/{schema_response._id}/versions/',
                            'meta': {}
                        }
                    }
                }
            },
            'type': 'schema_responses'
        }
