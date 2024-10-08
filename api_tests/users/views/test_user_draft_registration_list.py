import pytest
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from api.users.views import UserDraftRegistrations
from api_tests.nodes.views.test_node_draft_registration_list import AbstractDraftRegistrationTestCase
from api_tests.utils import only_supports_methods
from osf.models import RegistrationSchema
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    DraftRegistrationFactory,
)
from osf.utils import permissions

SCHEMA_VERSION = 2


@pytest.mark.django_db
class TestUserDraftRegistrationList(AbstractDraftRegistrationTestCase):

    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return f'/{API_BASE}users/me/draft_registrations/'

    @pytest.fixture()
    def other_admin(self, project_public):
        user = AuthUserFactory()
        project_public.add_contributor(user, permissions=permissions.ADMIN, save=True)
        return user

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='Open-Ended Registration',
            schema_version=SCHEMA_VERSION
        )

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    def test_unacceptable_methods(self):
        assert only_supports_methods(UserDraftRegistrations, ['GET'])

    def test_non_contrib_view_permissions(
            self, app, user, other_admin, draft_registration, schema, url_draft_registrations
    ):
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

    def test_read_only_contributor_can_view_draft_list(
            self, app, draft_registration, user_read_contrib, url_draft_registrations
    ):
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth
        )
        assert len(res.json['data']) == 1

    def test_read_write_contributor_can_view_draft_list(
            self, app, user, other_admin, draft_registration, user_write_contrib, url_draft_registrations
    ):
        res = app.get(
            url_draft_registrations,
            auth=user_write_contrib.auth
        )
        assert len(res.json['data']) == 1

    def test_logged_in_non_contributor_cannot_view_draft_list(
            self, app, user, draft_registration, user_non_contrib, url_draft_registrations
    ):
        res = app.get(
            url_draft_registrations,
            auth=user_non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_unauthenticated_user_cannot_view_draft_list(self, app, url_draft_registrations):
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    def test_deleted_draft_registration_does_not_show_up_in_draft_list(
            self, app, user, draft_registration, url_draft_registrations):
        draft_registration.deleted = timezone.now()
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 0

    def test_deleted_node_does_not_show_up_in_draft_list(
            self, app, user, project_public, draft_registration, url_draft_registrations):
        project_public.deleted = timezone.now()
        project_public.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 0

    def test_draft_with_registered_node_does_not_show_up_in_draft_list(
            self, app, user, project_public, draft_registration, url_draft_registrations):
        reg = RegistrationFactory(project=project_public, draft_registration=draft_registration)
        draft_registration.registered_node = reg
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 0

    def test_draft_with_deleted_registered_node_shows_up_in_draft_list(
            self, app, user, project_public,
            draft_registration, schema,
            url_draft_registrations):
        reg = RegistrationFactory(project=project_public, draft_registration=draft_registration)
        draft_registration.registered_node = reg
        draft_registration.save()
        reg.deleted = timezone.now()
        reg.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

    def test_cannot_access_other_users_draft_registration(self, app, user, other_admin, draft_registration, schema):
        res = app.get(
            f'/{API_BASE}users/{user._id}/draft_registrations/',
            auth=other_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_can_access_own_draft_registrations_with_guid(self, app, user, draft_registration):
        url = f'/{API_BASE}users/{user._id}/draft_registrations/'
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
