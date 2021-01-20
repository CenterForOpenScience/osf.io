import binascii
import hashlib
import pytest

from api.base.settings.defaults import API_BASE
from django.contrib.auth.models import Permission

from osf.models import RegistrationSchema
from osf_tests.factories import (
    ProjectFactory,
    DraftRegistrationFactory,
    AuthUserFactory,
    RegistrationFactory,
)
from osf.utils.permissions import WRITE, READ, ADMIN
from rest_framework import exceptions
from api_tests.nodes.views.test_node_draft_registration_list import DraftRegistrationTestCase

SCHEMA_VERSION = 2


@pytest.mark.django_db
class TestDraftRegistrationDetail(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}nodes/{}/draft_registrations/{}/?{}'.format(
            API_BASE, project_public._id, draft_registration._id, 'version=2.19')

    def test_admin_can_view_draft(
            self, app, user, draft_registration, project_public,
            schema, url_draft_registrations, group_mem):
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['id'] == draft_registration._id
        assert data['attributes']['registration_metadata'] == {}

    def test_admin_group_member_can_view(
        self, app, user, draft_registration, project_public,
            schema, url_draft_registrations, group_mem):

        res = app.get(url_draft_registrations, auth=group_mem.auth)
        assert res.status_code == 200

    def test_cannot_view_draft(
            self, app, user_write_contrib, project_public,
            user_read_contrib, user_non_contrib,
            url_draft_registrations, group, group_mem):

        #   test_read_only_contributor_cannot_view_draft
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_view_draft
        res = app.get(
            url_draft_registrations,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_view_draft
        res = app.get(
            url_draft_registrations,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_draft
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    #   test_group_mem_read_cannot_view
        project_public.remove_osf_group(group)
        project_public.add_osf_group(group, READ)
        res = app.get(url_draft_registrations, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 403

    def test_cannot_view_deleted_draft(
            self, app, user, url_draft_registrations):
        res = app.delete_json_api(url_draft_registrations, auth=user.auth)
        assert res.status_code == 204

        res = app.get(
            url_draft_registrations,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 410

    def test_draft_must_be_branched_from_node_in_kwargs(
            self, app, user, project_other, draft_registration):
        url = '/{}nodes/{}/draft_registrations/{}/'.format(
            API_BASE, project_other._id, draft_registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors'][0]
        assert errors['detail'] == 'This draft registration is not created from the given node.'

    def test_draft_registration_serializer_usage(self, app, user, project_public, draft_registration):
        # Tests the usage of DraftRegistrationDetailSerializer for version 2.20
        url_draft_registrations = '/{}nodes/{}/draft_registrations/{}/?{}'.format(
            API_BASE, project_public._id, draft_registration._id, 'version=2.20')

        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        # Set of fields that DraftRegistrationDetailLegacySerializer does not provide
        assert data['attributes']['title']
        assert data['attributes']['description']
        assert data['relationships']['affiliated_institutions']

    def test_can_view_after_added(
            self, app, schema, draft_registration, url_draft_registrations):
        user = AuthUserFactory()
        project = draft_registration.branched_from
        project.add_contributor(user, ADMIN)
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestDraftRegistrationUpdate(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def schema_prereg(self):
        return RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration_prereg(self, user, project_public, schema_prereg):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema_prereg,
            branched_from=project_public
        )

    @pytest.fixture()
    def metadata_registration(
            self, metadata,
            draft_registration_prereg):
        return metadata(draft_registration_prereg)

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}nodes/{}/draft_registrations/{}/?{}'.format(
            API_BASE, project_public._id, draft_registration._id, 'version=2.19')

    @pytest.fixture()
    def payload(self, draft_registration):
        return {
            'data': {
                'id': draft_registration._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'datacompletion': {
                            'value': 'No, data collection has not begun'
                        },
                        'looked': {
                            'value': 'No'
                        },
                        'comments': {
                            'value': 'This is my first registration.'
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def payload_with_registration_responses(self, draft_registration):
        return {
            'data': {
                'id': draft_registration._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_responses': {
                        'datacompletion': 'No, data collection has not begun',
                        'looked': 'No',
                        'comments': 'This is my first registration.'
                    }
                }
            }
        }

    def test_id_required_in_payload(self, app, user, url_draft_registrations):
        payload = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {}
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors'][0]
        assert errors['source']['pointer'] == '/data/id'
        assert errors['detail'] == 'This field may not be null.'

    def test_admin_can_update_draft(
            self, app, user, schema, project_public,
            payload, url_draft_registrations):
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']
        # A write to registration_metadata, also updates registration_responses
        assert data['attributes']['registration_responses'] == {
            'datacompletion': 'No, data collection has not begun',
            'looked': 'No',
            'comments': 'This is my first registration.'
        }

    def test_draft_must_be_branched_from_node(
            self, app, user, project_other, draft_registration, payload):
        url = '/{}nodes/{}/draft_registrations/{}/'.format(
            API_BASE, project_other._id, draft_registration._id)
        res = app.put_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors'][0]
        assert errors['detail'] == 'This draft registration is not created from the given node.'

    def test_cannot_update_draft(
            self, app, user_write_contrib, project_public,
            user_read_contrib, user_non_contrib,
            payload, url_draft_registrations, group, group_mem):

        #   test_read_only_contributor_cannot_update_draft
        res = app.put_json_api(
            url_draft_registrations,
            payload,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_update_draft
        res = app.put_json_api(
            url_draft_registrations,
            payload,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_update_draft
        res = app.put_json_api(
            url_draft_registrations,
            payload, expect_errors=True)
        assert res.status_code == 401

    #   test_osf_group_member_admin_cannot_update_draft
        res = app.put_json_api(
            url_draft_registrations,
            payload, expect_errors=True,
            auth=group_mem.auth
        )
        assert res.status_code == 403

    #   test_osf_group_member_write_cannot_update_draft
        project_public.remove_osf_group(group)
        project_public.add_osf_group(group, WRITE)
        res = app.put_json_api(
            url_draft_registrations,
            payload, expect_errors=True,
            auth=group_mem.auth
        )
        assert res.status_code == 403

    def test_registration_metadata_does_not_need_to_be_supplied(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes'] = {}

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200

    def test_registration_metadata_must_be_a_dictionary(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata'] = 'Registration data'

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['source']['pointer'] == '/data/attributes/registration_metadata'
        assert errors['detail'] == 'Expected a dictionary of items but got type "str".'

    def test_registration_metadata_question_values_must_be_dictionaries(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['datacompletion'] = 'No, data collection has not begun'

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration your response to the \'Data collection status\'' \
                                   ' field is invalid, your response must be one of the provided options.'

    def test_registration_metadata_question_keys_must_be_value(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            'incorrect_key': 'No, data collection has not begun'}

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration your response to the \'Data collection status\'' \
                                   ' field is invalid, your response must be one of the provided options.'

    def test_question_in_registration_metadata_must_be_in_schema(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q11'] = {
            'value': 'No, data collection has not begun'
        }

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration the \'datacompletion\' field is extraneous and not' \
                                   ' permitted in your response.'

    def test_multiple_choice_question_value_must_match_value_in_schema(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            'value': 'Nope, data collection has not begun'}

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration your response to the \'Data collection status\' field' \
                                   ' is invalid, your response must be one of the provided options.'

    def test_cannot_update_registration_schema(
            self, app, user, schema, payload,
            schema_prereg, url_draft_registrations):
        payload['data']['relationships'] = {
            'registration_schema': {
                'data': {
                    'id': schema_prereg._id,
                    'type': 'registration_schema'
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert schema._id in res.json['data']['relationships']['registration_schema']['links']['related']['href']

    def test_required_metaschema_questions_not_required_on_update(
            self, app, user, project_public,
            draft_registration_prereg,
            metadata_registration):

        url = '/{}nodes/{}/draft_registrations/{}/'.format(
            API_BASE, project_public._id, draft_registration_prereg._id)

        del metadata_registration['q1']
        draft_registration_prereg.metadata_registration = metadata_registration
        draft_registration_prereg.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'q3': {
                            'value': 'New response'
                        }
                    }
                }
            }
        }

        res = app.put_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q3']['value'] == 'New response'
        assert 'q1' not in res.json['data']['attributes']['registration_metadata']

    def test_required_registration_responses_questions_not_required_on_update(
            self, app, user, project_public, draft_registration_prereg):

        url = '/{}nodes/{}/draft_registrations/{}/'.format(
            API_BASE, project_public._id, draft_registration_prereg._id)

        registration_responses = {
            'q1': 'First question answered'
        }

        draft_registration_prereg.registration_responses = {}
        draft_registration_prereg.registration_metadata = {}
        draft_registration_prereg.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_responses': registration_responses
                }
            }
        }

        res = app.put_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q1']['value'] == registration_responses['q1']
        assert res.json['data']['attributes']['registration_responses']['q1'] == registration_responses['q1']

    def test_registration_responses_must_be_a_dictionary(
            self, app, user, payload_with_registration_responses, url_draft_registrations):
        payload_with_registration_responses['data']['attributes']['registration_responses'] = 'Registration data'

        res = app.put_json_api(
            url_draft_registrations,
            payload_with_registration_responses, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['source']['pointer'] == '/data/attributes/registration_responses'
        assert errors['detail'] == 'Expected a dictionary of items but got type "str".'

    def test_registration_responses_question_values_should_not_be_dicts(
            self, app, user, payload_with_registration_responses, url_draft_registrations):
        payload_with_registration_responses['data']['attributes']['registration_responses']['datacompletion'] = {'value': 'No, data collection has not begun'}

        res = app.put_json_api(
            url_draft_registrations,
            payload_with_registration_responses, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration, your response to the \'Data collection status\'' \
                                   ' field is invalid, your response must be one of the provided options.'

    def test_question_in_registration_responses_must_be_in_schema(
            self, app, user, payload_with_registration_responses, url_draft_registrations):
        payload_with_registration_responses['data']['attributes']['registration_responses']['q11'] = {
            'value': 'No, data collection has not begun'
        }

        res = app.put_json_api(
            url_draft_registrations,
            payload_with_registration_responses, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'Additional properties are not allowed (\'q11\' was unexpected)'

    def test_multiple_choice_question_value_in_registration_responses_must_match_value_in_schema(
            self, app, user, payload_with_registration_responses, url_draft_registrations):
        payload_with_registration_responses['data']['attributes']['registration_responses']['datacompletion'] = 'Nope, data collection has not begun'

        res = app.put_json_api(
            url_draft_registrations,
            payload_with_registration_responses, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration, your response to the \'Data collection status\' field' \
                                   ' is invalid, your response must be one of the provided options.'


@pytest.mark.django_db
class TestDraftRegistrationPatch(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def schema_prereg(self):
        return RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration_prereg(self, user, project_public, schema_prereg):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema_prereg,
            branched_from=project_public
        )

    @pytest.fixture()
    def metadata_registration(self, metadata, draft_registration_prereg):
        return metadata(draft_registration_prereg)

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}nodes/{}/draft_registrations/{}/?{}'.format(
            API_BASE, project_public._id, draft_registration._id, 'version=2.19')

    @pytest.fixture()
    def payload(self, draft_registration):
        return {
            'data': {
                'id': draft_registration._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'datacompletion': {
                            'value': 'No, data collection has not begun'
                        },
                        'looked': {
                            'value': 'No'
                        },
                        'comments': {
                            'value': 'This is my first registration.'
                        }
                    }
                }
            }
        }

    def test_admin_can_update_draft(
            self, app, user, schema, payload,
            url_draft_registrations):
        res = app.patch_json_api(
            url_draft_registrations,
            payload, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']

    def test_cannot_update_draft(
            self, app, user_write_contrib,
            user_read_contrib, user_non_contrib,
            payload, url_draft_registrations, group_mem):

        #   test_read_only_contributor_cannot_update_draft
        res = app.patch_json_api(
            url_draft_registrations,
            payload,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_update_draft
        res = app.patch_json_api(
            url_draft_registrations,
            payload,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_update_draft
        res = app.patch_json_api(
            url_draft_registrations,
            payload, expect_errors=True)
        assert res.status_code == 401

        # group admin cannot update draft
        res = app.patch_json_api(
            url_draft_registrations,
            payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 403

@pytest.mark.django_db
class TestDraftRegistrationDelete(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}nodes/{}/draft_registrations/{}/?{}'.format(
            API_BASE, project_public._id, draft_registration._id, 'version=2.19')

    def test_admin_can_delete_draft(self, app, user, url_draft_registrations, project_public):
        res = app.delete_json_api(url_draft_registrations, auth=user.auth)
        assert res.status_code == 204

    def test_cannot_delete_draft(
            self, app, user_write_contrib, project_public,
            user_read_contrib, user_non_contrib,
            url_draft_registrations, group, group_mem):

        #   test_read_only_contributor_cannot_delete_draft
        res = app.delete_json_api(
            url_draft_registrations,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_delete_draft
        res = app.delete_json_api(
            url_draft_registrations,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_delete_draft
        res = app.delete_json_api(
            url_draft_registrations,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_delete_draft
        res = app.delete_json_api(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    #   test_group_member_admin_cannot_delete_draft
        res = app.delete_json_api(url_draft_registrations, expect_errors=True, auth=group_mem.auth)
        assert res.status_code == 403

    #   test_group_member_write_cannot_delete_draft
        project_public.remove_osf_group(group)
        project_public.add_osf_group(group, WRITE)
        res = app.delete_json_api(url_draft_registrations, expect_errors=True, auth=group_mem.auth)
        assert res.status_code == 403

    def test_draft_that_has_been_registered_cannot_be_deleted(
            self, app, user, project_public, draft_registration, url_draft_registrations):
        reg = RegistrationFactory(project=project_public)
        draft_registration.registered_node = reg
        draft_registration.save()
        res = app.delete_json_api(
            url_draft_registrations,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'This draft has already been registered and cannot be modified.'

    def test_reviewer_cannot_delete_draft_registration(
            self, app, url_draft_registrations):
        user = AuthUserFactory()
        administer_permission = Permission.objects.get(
            codename='administer_prereg')
        user.user_permissions.add(administer_permission)
        user.save()

        res = app.delete_json_api(
            url_draft_registrations,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail


@pytest.mark.django_db
class TestDraftPreregChallengeRegistrationMetadataValidation(
        DraftRegistrationTestCase):

    @pytest.fixture()
    def schema_prereg(self):
        return RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration_prereg(self, user, project_public, schema_prereg):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema_prereg,
            branched_from=project_public
        )

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(
            self, project_public,
            draft_registration_prereg):
        return '/{}nodes/{}/draft_registrations/{}/?{}'.format(
            API_BASE, project_public._id, draft_registration_prereg._id, 'version=2.19')

    @pytest.fixture()
    def payload(self, draft_registration_prereg):
        return {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {}
                }
            }
        }

    def test_first_level_open_ended_answers(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'value': 'This is my answer.'
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q1']['value'] == 'This is my answer.'

    def test_first_level_open_ended_answer_must_have_correct_key(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'values': 'This is my answer.'
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0][
            'detail'] == 'For your registration your response to the \'Title\' field is invalid.'

    def test_first_level_open_ended_answer_must_be_of_correct_type(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'value': 12345
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Title\' field is invalid.'

    def test_first_level_open_ended_answer_not_expecting_more_nested_data(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'value': {
                'question': {
                    'value': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Title\' field is invalid.'

    def test_second_level_answers(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': {
                    'value': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q7']['value']['question']['value'] == 'This is my answer.'

    def test_second_level_open_ended_answer_must_have_correct_key(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'questions': {
                    'value': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0][
            'detail'] == 'For your registration your response to the \'Data collection procedures\' field is invalid.'

    def test_third_level_open_ended_answer_must_have_correct_key(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': {
                    'values': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == \
               'For your registration your response to the \'Data collection procedures\' field is invalid.'

    def test_second_level_open_ended_answer_must_have_correct_type(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': 'This is my answer'
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Data collection procedures\'' \
                                                  ' field is invalid.'

    def test_third_level_open_ended_answer_must_have_correct_type(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': {
                    'value': True
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Data collection procedures\'' \
                                                  ' field is invalid.'

    def test_uploader_metadata(
            self, app, user, project_public,
            draft_registration_prereg,
            payload, url_draft_registrations):
        sha256 = hashlib.pbkdf2_hmac('sha256', b'password', b'salt', 100000)
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'uploader': {
                    'value': 'Screen Shot 2016-03-30 at 7.02.05 PM.png',
                    'extra': [{
                        'data': {},
                        'nodeId': project_public._id,
                        'viewUrl': '/project/{}/files/osfstorage/{}'.format(project_public._id, draft_registration_prereg._id),
                        'selectedFileName': 'Screen Shot 2016-03-30 at 7.02.05 PM.png',
                        'sha256': binascii.hexlify(sha256).decode()
                    }]
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q7']['value'][
            'uploader']['value'] == 'Screen Shot 2016-03-30 at 7.02.05 PM.png'

    def test_uploader_metadata_incorrect_key(
            self, app, user, project_public,
            draft_registration_prereg,
            payload, url_draft_registrations):
        sha256 = hashlib.pbkdf2_hmac('sha256', b'password', b'salt', 100000)
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'uploader': {
                    'value': 'Screen Shot 2016-03-30 at 7.02.05 PM.png',
                    'extra': [{
                        'data': {},
                        'nodeId': project_public._id,
                        'viewUrl': '/project/{}/files/osfstorage/{}'.format(project_public._id, draft_registration_prereg._id),
                        'selectedFileNames': 'Screen Shot 2016-03-30 at 7.02.05 PM.png',
                        'sha256': binascii.hexlify(sha256).decode()
                    }]
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0][
            'detail'] == 'For your registration your response to the \'Data collection procedures\' field is invalid.'

    def test_multiple_choice_questions_incorrect_choice(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q15'] = {
            'value': ['This is my answer.']
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Blinding\' field is invalid, your ' \
                                                  'response must be one of the provided options.'

    def test_multiple_choice_questions(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q15'] = {
            'value': ['No blinding is involved in this study.']
        }
        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q15']['value'] == ['No blinding is involved in this study.']
