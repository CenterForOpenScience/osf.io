import pytest
from urlparse import urlparse

from rest_framework import exceptions
from api.base.settings.defaults import API_BASE
from osf.utils import permissions
from osf.models import Registration, NodeLog
from framework.auth import Auth
from api.registrations.serializers import RegistrationSerializer, RegistrationDetailSerializer
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    RegistrationApprovalFactory,
    AuthUserFactory,
    WithdrawnRegistrationFactory,
)
from tests.utils import assert_latest_log


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRegistrationDetail:

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(
            title='Public Project',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(title='Private Project', creator=user)

    @pytest.fixture()
    def public_registration(self, user, public_project):
        return RegistrationFactory(
            project=public_project,
            creator=user,
            is_public=True)

    @pytest.fixture()
    def private_registration(self, user, private_project):
        return RegistrationFactory(project=private_project, creator=user)

    @pytest.fixture()
    def public_url(self, public_registration):
        return '/{}registrations/{}/'.format(API_BASE, public_registration._id)

    @pytest.fixture()
    def private_url(self, private_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, private_registration._id)

    def test_registration_detail(
            self, app, user, public_project, private_project,
            public_registration, private_registration,
            public_url, private_url):

        non_contributor = AuthUserFactory()

    #   test_return_public_registration_details_logged_out
        res = app.get(public_url)
        assert res.status_code == 200
        data = res.json['data']
        registered_from = urlparse(
            data['relationships']['registered_from']['links']['related']['href']
        ).path
        assert data['attributes']['registration'] is True
        assert registered_from == '/{}nodes/{}/'.format(
            API_BASE, public_project._id)

    #   test_return_public_registration_details_logged_in
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        data = res.json['data']
        registered_from = urlparse(
            data['relationships']['registered_from']['links']['related']['href']).path
        assert data['attributes']['registration'] is True
        assert registered_from == '/{}nodes/{}/'.format(
            API_BASE, public_project._id)

    #   test_return_private_registration_details_logged_out
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_project_registrations_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        data = res.json['data']
        registered_from = urlparse(
            data['relationships']['registered_from']['links']['related']['href']).path
        assert data['attributes']['registration'] is True
        assert registered_from == '/{}nodes/{}/'.format(
            API_BASE, private_project._id)

    #   test_return_private_registration_details_logged_in_non_contributor
        res = app.get(
            private_url,
            auth=non_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_do_not_return_node_detail
        url = '/{}registrations/{}/'.format(API_BASE, public_project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    #   test_do_not_return_node_detail_in_sub_view
        url = '/{}registrations/{}/contributors/'.format(
            API_BASE, public_project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    #   test_do_not_return_registration_in_node_detail
        url = '/{}nodes/{}/'.format(API_BASE, public_registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    #   test_registration_shows_specific_related_counts
        url = '/{}registrations/{}/?related_counts=children'.format(
            API_BASE, private_registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0
        assert res.json['data']['relationships']['contributors']['links']['related']['meta'] == {}

    #   test_hide_if_registration
        # Registrations are a HideIfRegistration field
        node_url = '/{}nodes/{}/'.format(API_BASE, private_project._id)
        res = app.get(node_url, auth=user.auth)
        assert res.status_code == 200
        assert 'registrations' in res.json['data']['relationships']

        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert 'registrations' not in res.json['data']['relationships']


@pytest.mark.django_db
class TestRegistrationUpdate:

    @pytest.fixture()
    def read_only_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_write_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration_approval(self, user):
        return RegistrationApprovalFactory(
            state='unapproved', approve=False, user=user)

    @pytest.fixture()
    def unapproved_registration(self, registration_approval):
        return Registration.objects.get(
            registration_approval=registration_approval)

    @pytest.fixture()
    def unapproved_url(self, unapproved_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, unapproved_registration._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(
            title='Public Project',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(title='Private Project', creator=user)

    @pytest.fixture()
    def public_registration(self, user, public_project):
        return RegistrationFactory(
            project=public_project,
            creator=user,
            is_public=True)

    @pytest.fixture()
    def private_registration(
            self, user, private_project, read_only_contributor,
            read_write_contributor):
        private_registration = RegistrationFactory(
            project=private_project, creator=user)
        private_registration.add_contributor(
            read_only_contributor, permissions=[
                permissions.READ])
        private_registration.add_contributor(
            read_write_contributor, permissions=[
                permissions.WRITE])
        private_registration.save()
        return private_registration

    @pytest.fixture()
    def public_url(self, public_registration):
        return '/{}registrations/{}/'.format(API_BASE, public_registration._id)

    @pytest.fixture()
    def private_url(self, private_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, private_registration._id)

    @pytest.fixture()
    def attributes(self):
        return {'public': True}

    @pytest.fixture()
    def make_payload(self, private_registration, attributes):
        def payload(
                id=private_registration._id,
                type='registrations',
                attributes=attributes
        ):
            return {
                'data': {
                    'id': id,
                    'type': type,
                    'attributes': attributes
                }
            }
        return payload

    def test_update_registration(
            self, app, user, read_only_contributor,
            read_write_contributor, public_registration,
            public_url, private_url, make_payload):

        private_registration_payload = make_payload()
        non_contributor = AuthUserFactory()

    #   test_update_private_registration_logged_out
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            expect_errors=True)
        assert res.status_code == 401

    #   test_update_private_registration_logged_in_admin
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is True

    #   test_update_private_registration_logged_in_read_only_contributor
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            auth=read_only_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_update_private_registration_logged_in_read_write_contributor
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            auth=read_write_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_update_public_registration_to_private
        public_to_private_payload = make_payload(
            id=public_registration._id, attributes={'public': False})

        res = app.put_json_api(
            public_url,
            public_to_private_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registrations can only be turned from private to public.'

        res = app.put_json_api(
            public_url,
            public_to_private_payload,
            auth=non_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_fields(
            self, app, user, public_registration,
            private_registration, public_url,
            private_url, make_payload):

        #   test_public_field_has_invalid_value
        invalid_public_payload = make_payload(
            id=public_registration._id,
            attributes={'public': 'Dr.Strange'})

        res = app.put_json_api(
            public_url,
            invalid_public_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"Dr.Strange" is not a valid boolean.'

    #   test_fields_other_than_public_are_ignored
        attribute_list = {
            'public': True,
            'category': 'instrumentation',
            'title': 'New title',
            'description': 'New description'
        }
        verbose_private_payload = make_payload(attributes=attribute_list)

        res = app.put_json_api(
            private_url,
            verbose_private_payload,
            auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is True
        assert res.json['data']['attributes']['category'] == 'project'
        assert res.json['data']['attributes']['description'] == private_registration.description
        assert res.json['data']['attributes']['title'] == private_registration.title

    #   test_type_field_must_match
        node_type_payload = make_payload(type='node')

        res = app.put_json_api(
            private_url,
            node_type_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_id_field_must_match
        mismatch_id_payload = make_payload(id='12345')

        res = app.put_json_api(
            private_url,
            mismatch_id_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    def test_turning_private_registrations_public(
            self, app, user, make_payload):
        private_project = ProjectFactory(creator=user, is_public=False)
        private_registration = RegistrationFactory(
            project=private_project, creator=user, is_public=False)

        private_to_public_payload = make_payload(id=private_registration._id)

        url = '/{}registrations/{}/'.format(API_BASE, private_registration._id)
        res = app.put_json_api(url, private_to_public_payload, auth=user.auth)
        assert res.json['data']['attributes']['public'] is True
        private_registration.reload()
        assert private_registration.is_public

    def test_registration_fields_are_read_only(self):
        writeable_fields = [
            'type',
            'public',
            'draft_registration',
            'registration_choice',
            'lift_embargo',
            'children',
            'tags']
        for field in RegistrationSerializer._declared_fields:
            reg_field = RegistrationSerializer._declared_fields[field]
            if field not in writeable_fields:
                assert getattr(reg_field, 'read_only', False) is True

    def test_registration_detail_fields_are_read_only(self):
        writeable_fields = [
            'type',
            'public',
            'draft_registration',
            'registration_choice',
            'lift_embargo',
            'children',
            'tags']

        for field in RegistrationDetailSerializer._declared_fields:
            reg_field = RegistrationSerializer._declared_fields[field]
            if field not in writeable_fields:
                assert getattr(reg_field, 'read_only', False) is True

    def test_user_cannot_delete_registration(self, app, user, private_url):
        res = app.delete_json_api(
            private_url,
            expect_errors=True,
            auth=user.auth)
        assert res.status_code == 405

    def test_make_public_unapproved_registration_raises_error(
            self, app, user, unapproved_registration, unapproved_url, make_payload):
        attribute_list = {
            'public': True,
            'withdrawn': True
        }
        unapproved_registration_payload = make_payload(
            id=unapproved_registration._id, attributes=attribute_list)

        res = app.put_json_api(
            unapproved_url,
            unapproved_registration_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'An unapproved registration cannot be made public.'


@pytest.mark.django_db
class TestRegistrationTags:

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user_admin, user_read_contrib):
        project_public = ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user_admin)
        project_public.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True)
        project_public.add_contributor(
            user_read_contrib,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            save=True)
        return project_public

    @pytest.fixture()
    def registration_public(self, project_public, user_admin):
        return RegistrationFactory(
            project=project_public,
            creator=user_admin,
            is_public=True)

    @pytest.fixture()
    def registration_private(self, project_public, user_admin):
        return RegistrationFactory(
            project=project_public,
            creator=user_admin,
            is_public=False)

    @pytest.fixture()
    def registration_withdrawn(self, project_public, user_admin):
        return RegistrationFactory(
            project=project_public,
            creator=user_admin,
            is_public=True)

    @pytest.fixture()
    def withdrawn_registration(self, registration_withdrawn, user_admin):
        registration_withdrawn.add_tag(
            'existing-tag', auth=Auth(user=user_admin))
        registration_withdrawn.save()
        withdrawn_registration = WithdrawnRegistrationFactory(
            registration=registration_withdrawn, user=user_admin)
        withdrawn_registration.justification = 'We made a major error.'
        withdrawn_registration.save()
        return withdrawn_registration

    @pytest.fixture()
    def url_registration_public(self, registration_public):
        return '/{}registrations/{}/'.format(
            API_BASE, registration_public._id)

    @pytest.fixture()
    def url_registration_private(self, registration_private):
        return '/{}registrations/{}/'.format(
            API_BASE, registration_private._id)

    @pytest.fixture()
    def url_registration_withdrawn(
            self, registration_withdrawn, withdrawn_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, registration_withdrawn._id)

    @pytest.fixture()
    def new_tag_payload_public(self, registration_public):
        return {
            'data': {
                'id': registration_public._id,
                'type': 'registrations',
                'attributes': {
                    'tags': ['new-tag'],
                }
            }
        }

    @pytest.fixture()
    def new_tag_payload_private(self, registration_private):
        return {
            'data': {
                'id': registration_private._id,
                'type': 'registrations',
                'attributes': {
                    'tags': ['new-tag'],
                }
            }
        }

    @pytest.fixture()
    def new_tag_payload_withdrawn(self, registration_withdrawn):
        return {
            'data': {
                'id': registration_withdrawn._id,
                'type': 'registrations',
                'attributes': {
                    'tags': ['new-tag', 'existing-tag'],
                }
            }
        }

    def test_registration_tags(
            self, app, registration_public, registration_private,
            url_registration_public, url_registration_private,
            new_tag_payload_public, new_tag_payload_private,
            user_admin, user_non_contrib):
        # test_registration_starts_with_no_tags
        res = app.get(url_registration_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

        # test_registration_does_not_expose_system_tags
        registration_public.add_system_tag('systag', save=True)
        res = app.get(url_registration_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

        # test_contributor_can_add_tag_to_public_registration
        with assert_latest_log(NodeLog.TAG_ADDED, registration_public):
            res = app.patch_json_api(
                url_registration_public,
                new_tag_payload_public,
                auth=user_admin.auth)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            registration_public.reload()
            assert registration_public.tags.count() == 1
            assert registration_public.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(url_registration_public)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

        # test_contributor_can_add_tag_to_private_registration
        with assert_latest_log(NodeLog.TAG_ADDED, registration_private):
            res = app.patch_json_api(
                url_registration_private,
                new_tag_payload_private,
                auth=user_admin.auth)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            registration_private.reload()
            assert registration_private.tags.count() == 1
            assert registration_private.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(
                url_registration_private,
                auth=user_admin.auth)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

        # test_non_contributor_cannot_add_tag_to_registration
        res = app.patch_json_api(
            url_registration_public,
            new_tag_payload_public,
            expect_errors=True,
            auth=user_non_contrib.auth)
        assert res.status_code == 403

        # test_partial_update_registration_does_not_clear_tagsb
        new_payload = {
            'data': {
                'id': registration_private._id,
                'type': 'registrations',
                'attributes': {
                    'public': True
                }
            }
        }
        res = app.patch_json_api(
            url_registration_private,
            new_payload,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1

    def test_tags_add_and_remove_properly(
            self, app, user_admin, registration_public,
            new_tag_payload_public, url_registration_public):
        with assert_latest_log(NodeLog.TAG_ADDED, registration_public):
            res = app.patch_json_api(
                url_registration_public,
                new_tag_payload_public,
                auth=user_admin.auth)
            assert res.status_code == 200
            # Ensure adding tag data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, registration_public), assert_latest_log(NodeLog.TAG_ADDED, registration_public, 1):
            # Ensure removing and adding tag data is correct from the PATCH
            # response
            res = app.patch_json_api(
                url_registration_public,
                {
                    'data': {
                        'id': registration_public._id,
                        'type': 'registrations',
                        'attributes': {'tags': ['newer-tag']}
                    }
                }, auth=user_admin.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'newer-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, registration_public):
            # Ensure removing tag data is correct from the PATCH response
            res = app.patch_json_api(
                url_registration_public,
                {
                    'data': {
                        'id': registration_public._id,
                        'type': 'registrations',
                        'attributes': {'tags': []}
                    }
                }, auth=user_admin.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 0

    def test_tags_for_withdrawn_registration(
            self, app, registration_withdrawn, user_admin,
            url_registration_withdrawn, new_tag_payload_withdrawn):
        res = app.patch_json_api(
            url_registration_withdrawn,
            new_tag_payload_withdrawn,
            auth=user_admin.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Cannot add tags to withdrawn registrations.'

        res = app.patch_json_api(
            url_registration_withdrawn,
            {
                'data': {
                    'id': registration_withdrawn._id,
                    'type': 'registrations',
                    'attributes': {'tags': []}
                }
            },
            auth=user_admin.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Cannot remove tags of withdrawn registrations.'
