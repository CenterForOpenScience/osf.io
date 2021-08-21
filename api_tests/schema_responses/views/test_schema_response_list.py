import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationSchemaFactory,
    AuthUserFactory,
    RegistrationFactory
)


@pytest.mark.django_db
class TestSchemaResponseList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'schema-responses',
                'attributes': {
                    'revision_justification': 'test justification'
                },
                'relationships': {
                    'registrations': {
                        'data': {
                            'type': 'registrations',
                            'id': registration._id
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def registration(self, schema):
        registration = RegistrationFactory(schema=schema)
        registration.save()
        return registration

    @pytest.fixture()
    def schema_response(self, user, registration, schema):
        return SchemaResponsesFactory(
            parent=registration,
            initiator=registration.creator,
            schema=schema
        )

    @pytest.fixture()
    def schema_response2(self, registration, schema):
        return SchemaResponsesFactory(
            parent=registration,
            initiator=registration.creator,
            schema=schema
        )

    @pytest.fixture()
    def url(self):
        return '/v2/schema_responses/'

    def test_schema_response_list(self, app, schema_response, schema_response2, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 2
        assert schema_response._id == data[0]['id']
        assert schema_response2._id == data[1]['id']
