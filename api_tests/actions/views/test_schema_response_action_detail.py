import pytest

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    SchemaResponseFactory,
    SchemaResponseActionFactory
)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestSchemaResponseActionDetail:

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
    def schema_response_action(self, schema_response):
        return SchemaResponseActionFactory(
            target=schema_response,
        )

    @pytest.fixture()
    def url(self, schema_response, schema_response_action):
        return f'/v2/schema_responses/{schema_response._id}/actions/{schema_response_action._id}/'

    def test_schema_response_action_detail(self, app, schema_response_action, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert schema_response_action._id == data['id']

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 200, ),
            ('read', 200, ),
            ('write', 200, ),
            ('admin', 200, ),
        ]
    )
    def test_schema_response_action_auth_get(self, app, registration, permission, user, expected_response, url):
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
    def test_schema_response_action_auth_post(self, app, registration, permission, user, expected_response, url):
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
    def test_schema_response_action_auth_patch(self, app, registration, permission, user, expected_response, url):
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
    def test_schema_response_action_delete(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response
