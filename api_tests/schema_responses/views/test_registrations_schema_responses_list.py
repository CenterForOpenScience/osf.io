import pytest

from django.utils import timezone

from osf_tests.factories import (
    # SchemaResponseFactory,
    RegistrationFactory,
    AuthUserFactory,
)

@pytest.fixture()
def perms_user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRegistrationsSchemaResponseListGETPermissions:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def url(self, registration):
        return f'/v2/registrations/{registration._id}/schema_responses/'

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_public_registration_responses_as_contributor(
            self, app, registration, url, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.is_public = True
        registration.save()
        resp = app.get(url, auth=perms_user.auth)

        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_public_registration_responses_as_non_contributor(
            self, app, registration, url, perms_user, use_auth):
        registration.is_public = True
        registration.save()
        resp = app.get(url, auth=perms_user.auth if use_auth else None)

        assert resp.status_code == 200

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_private_registration_responses_as_contributor(
            self, app, registration, url, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.is_public = False
        registration.save()
        resp = app.get(url, auth=perms_user.auth)

        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_private_registration_responses_as_non_contributor(
            self, app, registration, url, perms_user, use_auth):
        registration.is_public = False
        registration.save()
        resp = app.get(url, auth=perms_user.auth if use_auth else None)

        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_withdrawn_registration_responses_as_contributor(
            self, app, registration, url, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.moderation_state = 'withdrawn'
        registration.save()
        resp = app.get(url, auth=perms_user.auth)

        assert resp.status_code == 404

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_withdrawn_registration_responses_as_non_contributor(
            self, app, registration, url, perms_user, use_auth):
        registration.moderation_state = 'withdrawn'
        registration.save()
        resp = app.get(url, auth=perms_user.auth if use_auth else None)

        assert resp.status_code == 404

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_deleted_registration_responses_as_contributor(
            self, app, registration, url, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.deleted = timezone.now()
        registration.save()
        resp = app.get(url, auth=perms_user.auth)

        assert resp.status_code == 404

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_deleted_registration_responses_as_non_contributor(
            self, app, registration, url, perms_user, use_auth):
        registration.deleted = timezone.now()
        registration.save()
        resp = app.get(url, auth=perms_user.auth if use_auth else None)

        assert resp.status_code == 404

    def test_registrations_schema_responses_list(self, app, registration, schema_response, user, url):
        registration.is_public = True
        registration.save()
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 1
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
