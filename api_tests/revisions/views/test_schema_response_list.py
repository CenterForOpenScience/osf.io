
import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationSchemaFactory,
    AuthUserFactory,
    RegistrationFactory
)

from django.contrib.contenttypes.models import ContentType

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
                    'revision_justification': 'test justification'
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
        registration = RegistrationFactory(schema=schema)
        registration.save()
        return registration

    @pytest.fixture()
    def schema_response(self, user, node, schema):
        return SchemaResponsesFactory(parent=node, initiator=node.creator)

    @pytest.fixture()
    def schema_response2(self, node, schema):
        return SchemaResponsesFactory(parent=node, initiator=node.creator)

    @pytest.fixture()
    def url(self):
        return '/v2/revisions/'

    def test_schema_response_list(self, app, schema_response, schema_response2, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 2
        assert schema_response._id == data[0]['id']
        assert schema_response2._id == data[1]['id']

    def test_schema_response_create(self, app, node, user, payload, url):
        resp = app.post_json_api(url, payload, auth=user.auth)
        assert resp.status_code == 201
        data = resp.json['data']

        assert SchemaResponses.objects.count() == 1
        schema_response = SchemaResponses.objects.last()

        assert data['id'] == schema_response._id
