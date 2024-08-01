from unittest import mock
import pytest

from framework.auth.core import Auth
from django.utils import timezone
from api_tests.nodes.views.test_node_draft_registration_list import AbstractDraftRegistrationTestCase
from api.base.settings.defaults import API_BASE

from osf.migrations import ensure_invisible_and_inactive_schema
from osf.models import DraftRegistration, NodeLicense, RegistrationProvider, RegistrationSchema
from osf_tests.factories import (
    RegistrationFactory,
    CollectionFactory,
    ProjectFactory,
    AuthUserFactory,
    InstitutionFactory,
    DraftRegistrationFactory,
)
from osf.utils.permissions import READ, WRITE, ADMIN

from website import mails, settings


@pytest.fixture(autouse=True)
def invisible_and_inactive_schema():
    return ensure_invisible_and_inactive_schema()


@pytest.mark.django_db
class TestDraftRegistrationListTopLevelEndpoint:

    @pytest.fixture()
    def url_draft_registrations(self):
        return f'/{API_BASE}draft_registrations/'

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def group_mem(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(name='Open-Ended Registration', schema_version=3)

    @pytest.fixture()
    def draft_registration(self, user, project, schema, user_write_contrib, user_read_contrib, user_admin_contrib):
        draft = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project
        )
        draft.add_contributor(user_read_contrib, permissions=READ)
        draft.add_contributor(user_write_contrib, permissions=WRITE)
        draft.add_contributor(user_admin_contrib, permissions=ADMIN)
        return draft

    def test_read_only_contributor_can_view_draft_list(
            self, app, user_read_contrib, draft_registration, url_draft_registrations
    ):
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth
        )
        assert res.status_code == 200
        assert len(res.json['data']) == 1

    def test_read_write_contributor_can_view_draft_list(
            self, app, user_write_contrib, draft_registration, url_draft_registrations
    ):
        res = app.get(url_draft_registrations, auth=user_write_contrib.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

    def test_admin_can_view_draft_list(
            self, app, user_admin_contrib, draft_registration, schema, url_draft_registrations
    ):
        res = app.get(url_draft_registrations, auth=user_admin_contrib.auth)

        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1

        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

    def test_logged_in_non_contributor_has_empty_list(
            self, app, user_non_contrib, url_draft_registrations
    ):
        res = app.get(url_draft_registrations, auth=user_non_contrib.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

    def test_unauthenticated_user_cannot_view_draft_list(self, app, url_draft_registrations):
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    def test_logged_in_non_contributor_cannot_view_draft_list(self, app, user_non_contrib, url_draft_registrations):
        res = app.get(url_draft_registrations, auth=user_non_contrib.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

    def test_deleted_draft_registration_does_not_show_up_in_draft_list(self, app, user, draft_registration, url_draft_registrations):
        draft_registration.deleted = timezone.now()
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        assert not res.json['data']

    def test_draft_with_registered_node_does_not_show_up_in_draft_list(
            self, app, user, project, draft_registration, url_draft_registrations
    ):
        registration = RegistrationFactory(
            project=project,
            draft_registration=draft_registration
        )
        draft_registration.registered_node = registration
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        assert not res.json['data']

    def test_draft_with_deleted_registered_node_shows_up_in_draft_list(
            self, app, user, project, draft_registration, schema, url_draft_registrations
    ):
        registration = RegistrationFactory(project=project, draft_registration=draft_registration)
        draft_registration.registered_node = registration
        draft_registration.save()
        registration.deleted = timezone.now()
        registration.save()
        draft_registration.deleted = None
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}


class TestDraftRegistrationCreateWithNode(AbstractDraftRegistrationTestCase):

    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return f'/{API_BASE}draft_registrations/?'

    # Overrides `payload` in TestDraftRegistrationCreate`
    @pytest.fixture()
    def payload(self, metaschema_open_ended, provider, project_public):
        return {
            'data': {
                'type': 'draft_registrations',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': metaschema_open_ended._id
                        }
                    },
                    'branched_from': {
                        'data': {
                            'type': 'nodes',
                            'id': project_public._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }

    # Temporary alternative provider that supports `metaschema_open_ended` in `TestDraftRegistrationCreate`
    # This provider is created to fix the first 3 tests in this test class due to test DB changes with the
    # Django 3 Upgrade. A long-term solution is to create and/or use dedicated schemas for testing.
    @pytest.fixture()
    def provider_alt(self, metaschema_open_ended):
        default_provider = RegistrationProvider.get_default()
        default_provider.schemas.add(metaschema_open_ended)
        default_provider.save()
        return default_provider

    # Similarly, this is a temporary alternative payload that uses the above `provider_alt`.
    @pytest.fixture()
    def payload_alt(self, payload, provider_alt):
        new_payload = payload.copy()
        new_payload['data']['relationships']['provider']['data']['id'] = provider_alt._id
        return new_payload

    def test_cannot_create_draft_from_a_registration(self, app, user, payload_alt, project_public, url_draft_registrations):
        registration = RegistrationFactory(
            project=project_public,
            creator=user
        )
        payload_alt['data']['relationships']['branched_from']['data']['id'] = registration._id
        res = app.post_json_api(
            url_draft_registrations,
            payload_alt,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_cannot_create_draft_from_deleted_node(self, app, user, payload_alt, project_public, url_draft_registrations):
        project = ProjectFactory(is_public=True, creator=user)
        project.is_deleted = True
        project.save()
        payload_alt['data']['relationships']['branched_from']['data']['id'] = project._id
        res = app.post_json_api(
            url_draft_registrations,
            payload_alt,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 410
        assert res.json['errors'][0]['detail'] == 'The requested node is no longer available.'

    def test_cannot_create_draft_from_collection(self, app, user, payload_alt, project_public, url_draft_registrations):
        collection = CollectionFactory(creator=user)
        payload_alt['data']['relationships']['branched_from']['data']['id'] = collection._id
        res = app.post_json_api(
            url_draft_registrations, payload_alt, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_draft_registration_attributes_copied_from_node(
            self, app, project_public, url_draft_registrations, user, payload_alt
    ):

        write_contrib = AuthUserFactory()
        read_contrib = AuthUserFactory()

        GPL3 = NodeLicense.objects.get(license_id='GPL3')
        project_public.set_node_license(
            {
                'id': GPL3.license_id,
                'year': '1998',
                'copyrightHolders': ['Grapes McGee']
            },
            auth=Auth(user),
            save=True
        )

        project_public.add_contributor(write_contrib, WRITE)
        project_public.add_contributor(read_contrib, READ)

        # Only an admin can create a DraftRegistration
        res = app.post_json_api(url_draft_registrations, payload_alt, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.post_json_api(url_draft_registrations, payload_alt, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.post_json_api(url_draft_registrations, payload_alt, auth=user.auth)
        assert res.status_code == 201
        attributes = res.json['data']['attributes']
        assert attributes['title'] == project_public.title
        assert attributes['description'] == project_public.description
        assert attributes['category'] == project_public.category
        assert set(attributes['tags']) == {tag.name for tag in project_public.tags.all()}
        assert attributes['node_license']['year'] == '1998'
        assert attributes['node_license']['copyright_holders'] == ['Grapes McGee']

        relationships = res.json['data']['relationships']

        assert 'affiliated_institutions' in relationships
        assert 'subjects' in relationships
        assert 'contributors' in relationships

    def test_write_only_contributor_cannot_create_draft(
            self, app, user_write_contrib, project_public, payload_alt, url_draft_registrations
    ):
        assert user_write_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload_alt,
            auth=user_write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_read_only_contributor_cannot_create_draft(
            self, app, user_write_contrib, user_read_contrib, project_public, payload_alt, url_draft_registrations
    ):
        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload_alt,
            auth=user_read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_non_authenticated_user_cannot_create_draft(
            self, app, user_write_contrib, payload_alt, group, url_draft_registrations
    ):
        res = app.post_json_api(
            url_draft_registrations,
            payload_alt,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_logged_in_non_contributor_cannot_create_draft(
            self, app, user_non_contrib, payload_alt, url_draft_registrations
    ):

        res = app.post_json_api(
            url_draft_registrations,
            payload_alt,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_create_project_based_draft_does_not_email_initiator(self, app, user, url_draft_registrations, payload):
        with mock.patch.object(mails, 'send_mail') as mock_send_mail:
            app.post_json_api(f'{url_draft_registrations}?embed=branched_from&embed=initiator', payload, auth=user.auth)

        assert not mock_send_mail.called

    def test_affiliated_institutions_are_copied_from_node_no_institutions(self, app, user, url_draft_registrations, payload):
        """
        Draft registrations that are based on projects get those project's user institutional affiliation,
        those "no-project" registrations inherit the user's institutional affiliation.

        This tests a scenario where a user bases a registration on a node without affiliations, and so the
        draft registration has no institutional affiliation from the user or the node.
        """
        project = ProjectFactory(is_public=True, creator=user)
        payload['data']['relationships']['branched_from']['data']['id'] = project._id
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 201
        draft_registration = DraftRegistration.load(res.json['data']['id'])
        assert not draft_registration.affiliated_institutions.exists()

    def test_affiliated_institutions_are_copied_from_node(self, app, user, url_draft_registrations, payload):
        """
        Draft registrations that are based on projects get those project's user institutional affiliation,
        those "no-project" registrations inherit the user's institutional affiliation.

        This tests a scenario where a user bases their registration on a project that has a current institutional
        affiliation which is copied over to the draft registrations.
        """
        institution = InstitutionFactory()

        project = ProjectFactory(is_public=True, creator=user)
        project.affiliated_institutions.add(institution)
        payload['data']['relationships']['branched_from']['data']['id'] = project._id
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 201
        draft_registration = DraftRegistration.load(res.json['data']['id'])
        assert list(draft_registration.affiliated_institutions.all()) == list(project.affiliated_institutions.all())

    def test_affiliated_institutions_are_copied_from_user(self, app, user, url_draft_registrations, payload):
        """
        Draft registrations that are based on projects get those project's user institutional affiliation,
        those "no-project" registrations inherit the user's institutional affiliation.
        """
        institution = InstitutionFactory()
        user.add_or_update_affiliated_institution(institution)

        del payload['data']['relationships']['branched_from']
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 201
        draft_registration = DraftRegistration.load(res.json['data']['id'])
        assert list(draft_registration.affiliated_institutions.all()) == list(user.get_affiliated_institutions())


class TestDraftRegistrationCreateWithoutNode(AbstractDraftRegistrationTestCase):
    @pytest.fixture()
    def url_draft_registrations(self):
        return f'/{API_BASE}draft_registrations/?'

    # Overrides TestDraftRegistrationList
    def test_admin_can_create_draft(
            self, app, user, url_draft_registrations,
            payload, metaschema_open_ended):
        url = f'{url_draft_registrations}embed=branched_from&embed=initiator'
        res = app.post_json_api(url, payload, auth=user.auth)

        assert res.status_code == 201
        data = res.json['data']
        assert metaschema_open_ended._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == {}
        assert data['relationships']['provider']['links']['related']['href'] == \
               f'{settings.API_DOMAIN}v2/providers/registrations/{RegistrationProvider.default__id}/'

        assert data['embeds']['branched_from']['data']['id'] == DraftRegistration.objects.get(_id=data['id']).branched_from._id
        assert data['embeds']['initiator']['data']['id'] == user._id

        draft = DraftRegistration.load(data['id'])
        assert draft.creator == user
        assert draft.has_permission(user, ADMIN) is True

    def test_create_no_project_draft_emails_initiator(self, app, user, url_draft_registrations, payload):
        # Intercepting the send_mail call from website.project.views.contributor.notify_added_contributor
        with mock.patch.object(mails, 'send_mail') as mock_send_mail:
            resp = app.post_json_api(
                f'{url_draft_registrations}?embed=branched_from&embed=initiator',
                payload,
                auth=user.auth
            )
        assert mock_send_mail.called

        # Python 3.6 does not support mock.call_args.args/kwargs
        # Instead, mock.call_args[0] is positional args, mock.call_args[1] is kwargs
        # (note, this is compatible with later versions)
        mock_send_kwargs = mock_send_mail.call_args[1]
        assert mock_send_kwargs['mail'] == mails.CONTRIBUTOR_ADDED_DRAFT_REGISTRATION
        assert mock_send_kwargs['user'] == user
        assert mock_send_kwargs['node'] == DraftRegistration.load(resp.json['data']['id'])

    def test_create_draft_with_provider(
            self, app, user, url_draft_registrations, non_default_provider, payload_with_non_default_provider
    ):
        res = app.post_json_api(url_draft_registrations, payload_with_non_default_provider, auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['relationships']['provider']['links']['related']['href'] == \
               f'{settings.API_DOMAIN}v2/providers/registrations/{non_default_provider._id}/'

        draft = DraftRegistration.load(data['id'])
        assert draft.provider == non_default_provider

    def test_write_contrib(self, app, user, project_public, payload, url_draft_registrations, user_write_contrib):
        """(no node supplied, so any logged in user can create)
        """
        assert user_write_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth)
        assert res.status_code == 201

    def test_read_only(self, app, user, url_draft_registrations, user_read_contrib, project_public, payload):
        '''(no node supplied, so any logged in user can create)
        '''
        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_read_contrib.auth)
        assert res.status_code == 201

    def test_non_authenticated_user_cannot_create_draft(self, app, user, url_draft_registrations, payload):
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_logged_in_non_contributor(self, app, user, url_draft_registrations, user_non_contrib, payload):
        '''(no node supplied, so any logged in user can create)
        '''
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_non_contrib.auth
        )
        assert res.status_code == 201

    def test_draft_registration_attributes_not_copied_from_node(self, app, project_public,
            url_draft_registrations, user, payload):

        GPL3 = NodeLicense.objects.get(license_id='GPL3')
        project_public.set_node_license(
            {
                'id': GPL3.license_id,
                'year': '1998',
                'copyrightHolders': ['Grapes McGee']
            },
            auth=Auth(user),
            save=True
        )

        res = app.post_json_api(url_draft_registrations, payload, auth=user.auth)
        assert res.status_code == 201
        attributes = res.json['data']['attributes']
        assert attributes['title'] == ''
        assert attributes['description'] != project_public.description
        assert attributes['category'] != project_public.category
        assert set(attributes['tags']) != {tag.name for tag in project_public.tags.all()}
        assert attributes['node_license'] is None

        relationships = res.json['data']['relationships']

        assert 'affiliated_institutions' in relationships
        assert 'subjects' in relationships
        assert 'contributors' in relationships
