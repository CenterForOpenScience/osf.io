import pytest

from framework.auth.core import Auth
from api_tests.nodes.views.test_node_draft_registration_list import (
    TestDraftRegistrationList,
    TestDraftRegistrationCreate
)
from api.base.settings.defaults import API_BASE
from django.contrib.auth.models import Permission

from osf.models import DraftRegistration, NodeLicense, RegistrationProvider
from osf_tests.factories import (
    RegistrationFactory,
    CollectionFactory,
    ProjectFactory,
    AuthUserFactory
)
from osf.utils.permissions import READ, WRITE, ADMIN

from website import settings

@pytest.mark.django_db
class TestDraftRegistrationListNewWorkflow(TestDraftRegistrationList):
    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return '/{}draft_registrations/?'.format(API_BASE)

    # Overrides TestDraftRegistrationList
    def test_osf_group_with_admin_permissions_can_view(self):
        # DraftRegistration endpoints permissions are not calculated from the node
        return

    # Overrides TestDraftRegistrationList
    def test_cannot_view_draft_list(
            self, app, user_write_contrib, project_public,
            user_read_contrib, user_non_contrib, draft_registration,
            url_draft_registrations, group, group_mem):

        # test_read_only_contributor_can_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        #   test_read_write_contributor_can_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        #   test_logged_in_non_contributor_can_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        #   test_unauthenticated_user_cannot_view_draft_list
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401


class TestDraftRegistrationCreateWithNode(TestDraftRegistrationCreate):
    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return '/{}draft_registrations/?'.format(API_BASE)

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

    # Overrides TestDraftRegistrationList
    def test_cannot_create_draft_errors(
            self, app, user, project_public, payload, url_draft_registrations):
        #   test_cannot_create_draft_from_a_registration
        registration = RegistrationFactory(
            project=project_public, creator=user)
        payload['data']['relationships']['branched_from']['data']['id'] = registration._id
        res = app.post_json_api(
            url_draft_registrations, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    #   test_cannot_create_draft_from_deleted_node
        project = ProjectFactory(is_public=True, creator=user)
        project.is_deleted = True
        project.save()
        payload['data']['relationships']['branched_from']['data']['id'] = project._id
        res = app.post_json_api(
            url_draft_registrations, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 410
        assert res.json['errors'][0]['detail'] == 'The requested node is no longer available.'

    #   test_cannot_create_draft_from_collection
        collection = CollectionFactory(creator=user)
        payload['data']['relationships']['branched_from']['data']['id'] = collection._id
        res = app.post_json_api(
            url_draft_registrations, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_draft_registration_attributes_copied_from_node(self, app, project_public,
            url_draft_registrations, user, payload):

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

        res = app.post_json_api(url_draft_registrations, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 201
        res = app.post_json_api(url_draft_registrations, payload, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.post_json_api(url_draft_registrations, payload, auth=user.auth)
        assert res.status_code == 201
        attributes = res.json['data']['attributes']
        assert attributes['title'] == project_public.title
        assert attributes['description'] == project_public.description
        assert attributes['category'] == project_public.category
        assert set(attributes['tags']) == set([tag.name for tag in project_public.tags.all()])
        assert attributes['node_license']['year'] == '1998'
        assert attributes['node_license']['copyright_holders'] == ['Grapes McGee']

        relationships = res.json['data']['relationships']

        assert 'affiliated_institutions' in relationships
        assert 'subjects' in relationships
        assert 'contributors' in relationships

    def test_cannot_create_draft(
            self, app, user_write_contrib,
            user_read_contrib, user_non_contrib,
            project_public, payload, group,
            url_draft_registrations, group_mem):

        #   test_write_only_contributor_cannot_create_draft
        assert user_write_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 201

    #   test_read_only_contributor_cannot_create_draft
        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_non_authenticated_user_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload, expect_errors=True)
        assert res.status_code == 401

    #   test_logged_in_non_contributor_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_group_admin_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 201

    #   test_group_write_contrib_cannot_create_draft
        project_public.remove_osf_group(group)
        project_public.add_osf_group(group, WRITE)
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 201

    #   test_reviewer_cannot_create_draft_registration
        user = AuthUserFactory()
        administer_permission = Permission.objects.get(
            codename='administer_prereg')
        user.user_permissions.add(administer_permission)
        user.save()

        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 403


class TestDraftRegistrationCreateWithoutNode(TestDraftRegistrationCreate):
    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return '/{}draft_registrations/?'.format(API_BASE)

    # Overrides TestDraftRegistrationList
    def test_admin_can_create_draft(
            self, app, user, project_public, url_draft_registrations,
            payload, metaschema_open_ended):
        url = '{}embed=branched_from&embed=initiator'.format(url_draft_registrations)
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

    def test_create_draft_with_provider(self, app, user, url_draft_registrations, non_default_provider, payload_with_non_default_provider):

        res = app.post_json_api(url_draft_registrations, payload_with_non_default_provider, auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['relationships']['provider']['links']['related']['href'] == \
               f'{settings.API_DOMAIN}v2/providers/registrations/{non_default_provider._id}/'

        draft = DraftRegistration.load(data['id'])
        assert draft.provider == non_default_provider

    # Overrides TestDraftRegistrationList
    def test_cannot_create_draft(
            self, app, user_write_contrib,
            user_read_contrib, user_non_contrib,
            project_public, payload, group,
            url_draft_registrations, group_mem):

        #   test_write_contrib (no node supplied, so any logged in user can create)
        assert user_write_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth)
        assert res.status_code == 201

    #   test_read_only (no node supplied, so any logged in user can create)
        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_read_contrib.auth)
        assert res.status_code == 201

    #   test_non_authenticated_user_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload, expect_errors=True)
        assert res.status_code == 401

    #   test_logged_in_non_contributor (no node supplied, so any logged in user can create)
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_non_contrib.auth)
        assert res.status_code == 201

    # Overrides TestDraftRegistrationList
    def test_cannot_create_draft_errors(self):
        # The original test assumes a node is being passed in
        return

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
        assert attributes['title'] == 'Untitled'
        assert attributes['description'] != project_public.description
        assert attributes['category'] != project_public.category
        assert set(attributes['tags']) != set([tag.name for tag in project_public.tags.all()])
        assert attributes['node_license'] is None

        relationships = res.json['data']['relationships']

        assert 'affiliated_institutions' in relationships
        assert 'subjects' in relationships
        assert 'contributors' in relationships
