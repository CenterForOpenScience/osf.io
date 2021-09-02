import pytest

from osf_tests.factories import (
    SchemaResponseFactory,
    AuthUserFactory,
    RegistrationFactory
)


@pytest.mark.django_db
class TestSchemaResponseList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def schema_response(self, registration):
        return SchemaResponseFactory(
            registration=registration,
            initiator=registration.creator,
        )

    @pytest.fixture()
    def url(self):
        return '/v2/schema_responses/'

    def test_schema_response_list(self, app, registration, schema_response, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        assert registration.schema_responses.get()._id == data[0]['id']
