import pytest

from osf_tests.factories import (
    SchemaResponseFactory,
    RegistrationFactory,
    AuthUserFactory,
)


@pytest.mark.django_db
class TestRegistrationsSchemaResponseList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def schema_response(self, user, registration):
        return SchemaResponseFactory(
            registration=registration,
            initiator=registration.creator,
        )

    @pytest.fixture()
    def url(self, registration):
        return f'/v2/registrations/{registration._id}/schema_responses/'

    def test_registrations_schema_responses_list(self, app, registration, schema_response, user, url):
        schema_response.parent.is_public = True
        schema_response.parent.save()
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 2
        assert set(registration.schema_responses.values_list('_id', flat=True)) == {data[0]['id'], data[1]['id']}
