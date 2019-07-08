import pytest
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from api.users.views import UserDraftRegistrations
from api_tests.nodes.views.test_node_draft_registration_list import DraftRegistrationTestCase
from api_tests.utils import only_supports_methods
from osf.models import RegistrationSchema
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    DraftRegistrationFactory,
)
from osf.utils import permissions
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION


@pytest.mark.django_db
class TestDraftRegistrationList(DraftRegistrationTestCase):

    @pytest.fixture()
    def other_admin(self, project_public):
        user = AuthUserFactory()
        project_public.add_contributor(user, permissions=permissions.ADMIN, save=True)
        return user

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='Open-Ended Registration',
            schema_version=LATEST_SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return '/{}users/me/draft_registrations/'.format(API_BASE)

    def test_unacceptable_methods(self):
        assert only_supports_methods(UserDraftRegistrations, ['GET'])

    def test_view_permissions(
            self, app, user, other_admin, draft_registration,
            user_write_contrib, user_read_contrib, user_non_contrib,
            schema, url_draft_registrations):
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

        #   test_read_only_contributor_cannot_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth)
        assert len(res.json['data']) == 0

        #   test_read_write_contributor_cannot_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0

        #   test_logged_in_non_contributor_cannot_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_non_contrib.auth)
        assert len(res.json['data']) == 0

        #   test_unauthenticated_user_cannot_view_draft_list
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

    def test_draft_with_registered_node_does_not_show_up_in_draft_list(
            self, app, user, project_public, draft_registration, url_draft_registrations):
        reg = RegistrationFactory(project=project_public)
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
        reg = RegistrationFactory(project=project_public)
        draft_registration.registered_node = reg
        draft_registration.save()
        reg.is_deleted = True
        reg.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

    def test_cannot_access_other_users_draft_registration(
            self, app, user, other_admin, project_public,
            draft_registration, schema):
        url = '/{}users/{}/draft_registrations/'.format(API_BASE, user._id)
        res = app.get(url, auth=other_admin.auth, expect_errors=True)
        assert res.status_code == 403

    def test_can_access_own_draft_registrations_with_guid(
            self, app, user, draft_registration):
        url = '/{}users/{}/draft_registrations/'.format(API_BASE, user._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
