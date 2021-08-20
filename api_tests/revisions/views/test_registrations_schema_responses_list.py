import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationFactory,
    RegistrationSchemaFactory,
    AuthUserFactory,
)
from osf.models.schema_responses import SchemaResponses


@pytest.mark.django_db
class TestRegistrationsSchemaResponseList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, schema):
        return RegistrationFactory()

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data':
                {
                    'type': 'registrations',
                    'relationships': {
                        'registration': {
                            'data': {
                                'id': registration._id,
                                'type': 'schema_responses',
                                'attributes': {
                                    'revision_justification': "We're talkin' about practice..."
                                }
                            }
                        }
                    }
                }
        }

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def schema_response(self, user, registration, schema):
        return SchemaResponsesFactory(
            parent=registration,
            initiator=registration.creator,
            schema=registration.registered_schema.get(),
            revision_justification="We ain't even talking about the game.",
        )

    @pytest.fixture()
    def schema_response2(self, registration, schema):
        return SchemaResponsesFactory(
            parent=registration,
            initiator=registration.creator,
            schema=registration.registered_schema.get(),
            revision_justification="We ain't even talking about the game.",
        )

    @pytest.fixture()
    def url(self, registration):
        return f'/v2/registrations/{registration._id}/schema_responses/'

    def test_registrations_schema_responses_list(self, app, schema_response, schema_response2, user, url):
        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        schema_response.parent.is_public = True
        schema_response.parent.save()
        resp = app.get(url, auth=user.auth, expect_error=True)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 2
        assert schema_response2._id == data[0]['id']
        assert schema_response._id == data[1]['id']

    def test_registrations_schema_responses_list_create(self, app, registration, payload, user, url):
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        registration.add_contributor(user, 'admin')
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        data = resp.json['data']
        assert resp.status_code == 201
        assert SchemaResponses.objects.count() == 1
        schema_response = SchemaResponses.objects.last()

        assert data['id'] == schema_response._id
        assert schema_response.revision_justification == "We're talkin' about practice..."
