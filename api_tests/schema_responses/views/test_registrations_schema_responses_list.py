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
        registration.is_public = True
        registration.save()
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 2  # one created on registration, one by the factory
        assert schema_response._id == data[0]['id']

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 403, ),
            ('read', 200, ),
            ('write', 200, ),
            ('admin', 200, ),
        ]
    )
    def test_schema_response_auth_get(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 405, ),
            ('read', 405, ),
            ('write', 405, ),
            ('admin', 405, ),
        ]
    )
    def test_schema_response_auth_post(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 405, ),
            ('read', 405, ),
            ('write', 405, ),
            ('admin', 405, ),
        ]
    )
    def test_schema_response_auth_patch(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.patch_json_api(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 405, ),
            ('read', 405, ),
            ('write', 405, ),
            ('admin', 405, ),
        ]
    )
    def test_schema_response_auth_delete(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response
