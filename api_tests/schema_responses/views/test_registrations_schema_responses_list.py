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
            revision_justification="We ain't even talking about the game.",
        )

    @pytest.fixture()
    def schema_response2(self, registration):
        return SchemaResponseFactory(
            registration=registration,
            initiator=registration.creator,
            revision_justification="We're talkin' about practice.",
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
