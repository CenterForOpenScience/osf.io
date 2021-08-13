import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationSchemaFactory,
    AuthUserFactory,
    RegistrationFactory
)

from django.contrib.contenttypes.models import ContentType


@pytest.mark.django_db
class TestRegistrationsSchemaResponseDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def payload(self, node):
        return {
            'data': {
                'type': 'schema_responses',
                'attributes': {
                    'title': 'new title',
                    'responses': {
                        'q1': {'value': 'test'},
                    }
                }
            }
        }

    @pytest.fixture()
    def invalid_payload(self, node):
        return {
            'data': {
                'type': 'schema_responses',
                'attributes': {
                    'title': 'new title',
                    'responses': {
                        'oops': {'value': 'test'},
                        'q2': {'value': 'test2'},
                    }
                }
            }
        }

    @pytest.fixture()
    def schema_response(self, node, schema):
        content_type = ContentType.objects.get_for_model(node)
        return SchemaResponsesFactory(content_type=content_type, object_id=node.id, initiator=node.creator)

    @pytest.fixture()
    def schema_response_public(self, node, schema):
        content_type = ContentType.objects.get_for_model(node)
        return SchemaResponsesFactory(content_type=content_type, object_id=node.id, initiator=node.creator)

    @pytest.fixture()
    def schema_response_deleted(self, node, schema):
        content_type = ContentType.objects.get_for_model(node)
        return SchemaResponsesFactory(content_type=content_type, object_id=node.id, initiator=node.creator)

    @pytest.fixture()
    def url(self, node, schema_response):
        return f'/v2/registrations/{node._id}/revisions/{schema_response._id}/'

    def test_schema_response_detail(self, app, schema_response, schema_response_public, schema_response_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        import pprint
        pprint.pprint(resp.json)
        data = resp.json['data']
        assert data['id'] == schema_response._id

        assert False

    def test_schema_response_detail_update(self, app, schema_response, payload, user, url):
        resp = app.patch_json_api(url, payload, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id

        schema_response.refresh_from_db()
        assert schema_response.all_responses == {
            'q1': {'value': 'test'},
        }

    def test_schema_response_detail_validation(self, app, schema_response, invalid_payload, user, url):
        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == "For your registration the \'q1\' field is extraneous and not permitted in your response."

        schema_response.refresh_from_db()
        assert schema_response.all_responses == {}