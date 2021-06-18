import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationSchemaFactory,
    AuthUserFactory,
    RegistrationFactory
)
from django.utils import timezone

from osf.models import SchemaResponses

@pytest.mark.django_db
class TestSchemaResponseList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def payload(self, node):
        return {
            'data': {
                'type': 'schema_responses',
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
    def node(self, schema):
        registration = RegistrationFactory()
        registration.registered_schema.add(schema)
        registration.save()
        return registration

    @pytest.fixture()
    def schema_response(self, node, schema):
        return SchemaResponsesFactory(node=node, schema=schema)

    @pytest.fixture()
    def schema_response_public(self, node, schema):
        return SchemaResponsesFactory(public=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def schema_response_deleted(self, node, schema):
        return SchemaResponsesFactory(deleted=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def url(self):
        return '/v2/schema_responses/'

    def test_schema_response_list(self, app, schema_response, schema_response_public, schema_response_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 1
        assert schema_response_public._id == data[0]['id']

    def test_schema_response_create(self, app, node, user, payload, url):
        resp = app.post_json_api(url, payload, auth=user.auth)
        assert resp.status_code == 201
        data = resp.json['data']

        assert SchemaResponses.objects.count() == 1
        schema_response = SchemaResponses.objects.last()

        assert data['id'] == schema_response._id
