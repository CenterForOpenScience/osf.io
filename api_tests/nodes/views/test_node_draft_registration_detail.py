import binascii
import hashlib
import pytest

from api.base.settings.defaults import API_BASE
from osf.models import MetaSchema
from osf_tests.factories import (
    ProjectFactory,
    DraftRegistrationFactory,
    AuthUserFactory,
    RegistrationFactory,
)
from rest_framework import exceptions
from test_node_draft_registration_list import DraftRegistrationTestCase
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from website.settings import PREREG_ADMIN_TAG


@pytest.mark.django_db
class TestDraftRegistrationDetail(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return MetaSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=LATEST_SCHEMA_VERSION)

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
        return '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration._id)

    def test_admin_can_view_draft(self, app, user, draft_registration, schema, url_draft_registrations):
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['attributes']['registration_supplement'] == schema._id
        assert data['id'] == draft_registration._id
        assert data['attributes']['registration_metadata'] == {}

    def test_cannot_view_draft(self, app, user_write_contrib, user_read_contrib, user_non_contrib, url_draft_registrations):

    #   test_read_only_contributor_cannot_view_draft
        res = app.get(url_draft_registrations, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_view_draft
        res = app.get(url_draft_registrations, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_view_draft
        res = app.get(url_draft_registrations, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_draft
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    def test_draft_must_be_branched_from_node_in_kwargs(self, app, user, project_other, draft_registration):
        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_other._id, draft_registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors'][0]
        assert errors['detail'] == 'This draft registration is not created from the given node.'

    def test_reviewer_can_see_draft_registration(self, app, schema, draft_registration, url_draft_registrations):
        user = AuthUserFactory()
        user.add_system_tag(PREREG_ADMIN_TAG)
        user.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['attributes']['registration_supplement'] == schema._id
        assert data['id'] == draft_registration._id
        assert data['attributes']['registration_metadata'] == {}


@pytest.mark.django_db
class TestDraftRegistrationUpdate(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return MetaSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=LATEST_SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def schema_prereg(self):
        return MetaSchema.objects.get(name='Prereg Challenge', schema_version=LATEST_SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration_prereg(self, user, project_public, schema_prereg):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema_prereg,
            branched_from=project_public
        )

    @pytest.fixture()
    def metadata_registration(self, prereg_metadata, draft_registration_prereg):
        return prereg_metadata(draft_registration_prereg)

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration._id)

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

    def test_id_required_in_payload(self, app, user, url_draft_registrations):
        payload = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {}
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors'][0]
        assert errors['source']['pointer'] == '/data/id'
        assert errors['detail'] == 'This field may not be null.'

    def test_admin_can_update_draft(self, app, user, schema, payload, url_draft_registrations):
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['attributes']['registration_supplement'] == schema._id
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']

    def test_draft_must_be_branched_from_node(self, app, user, project_other, draft_registration, payload):
        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_other._id, draft_registration._id)
        res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors'][0]
        assert errors['detail'] == 'This draft registration is not created from the given node.'

    def test_cannot_update_draft(self, app, user_write_contrib, user_read_contrib, user_non_contrib, payload, url_draft_registrations):

    #   test_read_only_contributor_cannot_update_draft
        res = app.put_json_api(url_draft_registrations, payload, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_update_draft
        res = app.put_json_api(url_draft_registrations, payload, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_update_draft
        res = app.put_json_api(url_draft_registrations, payload, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_update_draft
        res = app.put_json_api(url_draft_registrations, payload, expect_errors=True)
        assert res.status_code == 401

    def test_registration_metadata_must_be_supplied(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes'] = {}

        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['source']['pointer'] == '/data/attributes/registration_metadata'
        assert errors['detail'] == 'This field is required.'

    def test_registration_metadata_must_be_a_dictionary(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata'] = 'Registration data'

        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['source']['pointer'] == '/data/attributes/registration_metadata'
        assert errors['detail'] == 'Expected a dictionary of items but got type "unicode".'

    def test_registration_metadata_question_values_must_be_dictionaries(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['datacompletion'] = 'No, data collection has not begun'

        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'u\'No, data collection has not begun\' is not of type \'object\''

    def test_registration_metadata_question_keys_must_be_value(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            'incorrect_key': 'No, data collection has not begun'
        }

        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'Additional properties are not allowed (u\'incorrect_key\' was unexpected)'

    def test_question_in_registration_metadata_must_be_in_schema(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q11'] = {
            'value': 'No, data collection has not begun'
        }

        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'Additional properties are not allowed (u\'q11\' was unexpected)'

    def test_multiple_choice_question_value_must_match_value_in_schema(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            'value': 'Nope, data collection has not begun'
        }

        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'u\'Nope, data collection has not begun\' is not one of [u\'No, data collection has not begun\', u\'Yes, data collection is underway or complete\']'

    def test_cannot_update_registration_schema(self, app, user, schema, payload, schema_prereg, url_draft_registrations):
        payload['data']['attributes']['registration_supplement'] = schema_prereg._id
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_supplement'] == schema._id

    def test_required_metaschema_questions_not_required_on_update(self, app, user, project_public, draft_registration_prereg, metadata_registration):

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration_prereg._id)

        del metadata_registration['q1']
        draft_registration_prereg.metadata_registration = metadata_registration
        draft_registration_prereg.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'q2': {
                            'value': 'New response'
                        }
                    }
                }
            }
        }

        res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q2']['value'] == 'New response'
        assert 'q1' not in res.json['data']['attributes']['registration_metadata']

    def test_reviewer_can_update_draft_registration(self, app, project_public, draft_registration_prereg):
        user = AuthUserFactory()
        user.add_system_tag(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'q2': {
                            'comments': [{'value': 'This is incomplete.'}]
                        }
                    }
                }
            }
        }

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration_prereg._id)


        res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q2']['comments'][0]['value'] == 'This is incomplete.'
        assert 'q1' not in res.json['data']['attributes']['registration_metadata']

    def test_reviewer_can_only_update_comment_fields_draft_registration(self, app, project_public, draft_registration_prereg):
        user = AuthUserFactory()
        user.add_system_tag(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'q2': {
                            'value': 'Test response'
                        }
                    }
                }
            }
        }

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration_prereg._id)

        res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Additional properties are not allowed (u\'value\' was unexpected)'

    def test_reviewer_can_update_nested_comment_fields_draft_registration(self, app, project_public, draft_registration_prereg):
        user = AuthUserFactory()
        user.add_system_tag(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'q7': {
                            'value': {
                                 'question': {
                                    'comments': [{'value': 'Add some clarity here.'}]
                                }
                            }
                        }
                    }
                }
            }
        }

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration_prereg._id)

        res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q7']['value']['question']['comments'][0]['value'] == 'Add some clarity here.'

    def test_reviewer_cannot_update_nested_value_fields_draft_registration(self, app, project_public, draft_registration_prereg):
        user = AuthUserFactory()
        user.add_system_tag(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            'data': {
                'id': draft_registration_prereg._id,
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': {
                        'q7': {
                            'value': {
                                 'question': {
                                    'value': 'This is the answer'
                                }
                            }
                        }
                    }
                }
            }
        }

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration_prereg._id)

        res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Additional properties are not allowed (u\'value\' was unexpected)'


@pytest.mark.django_db
class TestDraftRegistrationPatch(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return MetaSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=LATEST_SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def schema_prereg(self):
        return MetaSchema.objects.get(name='Prereg Challenge', schema_version=LATEST_SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration_prereg(self, user, project_public, schema_prereg):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema_prereg,
            branched_from=project_public
        )

    @pytest.fixture()
    def metadata_registration(self, prereg_metadata, draft_registration_prereg):
        return prereg_metadata(draft_registration_prereg)

    @pytest.fixture()
    def project_other(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration._id)

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

    def test_admin_can_update_draft(self, app, user, schema, payload, url_draft_registrations):
        res = app.patch_json_api(url_draft_registrations, payload, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['attributes']['registration_supplement'] == schema._id
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']

    def test_cannot_update_draft(self, app, user_write_contrib, user_read_contrib, user_non_contrib, payload, url_draft_registrations):

    #   test_read_only_contributor_cannot_update_draft
        res = app.patch_json_api(url_draft_registrations, payload, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_update_draft
        res = app.patch_json_api(url_draft_registrations, payload, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_update_draft
        res = app.patch_json_api(url_draft_registrations, payload, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_update_draft
        res = app.patch_json_api(url_draft_registrations, payload, expect_errors=True)
        assert res.status_code == 401


@pytest.mark.django_db
class TestDraftRegistrationDelete(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return MetaSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=LATEST_SCHEMA_VERSION)

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
        return '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration._id)

    def test_admin_can_delete_draft(self, app, user, url_draft_registrations):
        res = app.delete_json_api(url_draft_registrations, auth=user.auth)
        assert res.status_code == 204

    def test_cannot_delete_draft(self, app, user_write_contrib, user_read_contrib, user_non_contrib, url_draft_registrations):

    #   test_read_only_contributor_cannot_delete_draft
        res = app.delete_json_api(url_draft_registrations, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_delete_draft
        res = app.delete_json_api(url_draft_registrations, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_delete_draft
        res = app.delete_json_api(url_draft_registrations, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_delete_draft
        res = app.delete_json_api(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    def test_draft_that_has_been_registered_cannot_be_deleted(self, app, user, project_public, draft_registration, url_draft_registrations):
        reg = RegistrationFactory(project=project_public)
        draft_registration.registered_node = reg
        draft_registration.save()
        res = app.delete_json_api(url_draft_registrations, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'This draft has already been registered and cannot be modified.'

    def test_reviewer_cannot_delete_draft_registration(self, app, url_draft_registrations):
        user = AuthUserFactory()
        user.add_system_tag(PREREG_ADMIN_TAG)
        user.save()

        res = app.delete_json_api(url_draft_registrations, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail


@pytest.mark.django_db
class TestDraftPreregChallengeRegistrationMetadataValidation(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema_prereg(self):
        return MetaSchema.objects.get(name='Prereg Challenge', schema_version=LATEST_SCHEMA_VERSION)

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
    def url_draft_registrations(self, project_public, draft_registration_prereg):
        return '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, project_public._id, draft_registration_prereg._id)

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

    def test_first_level_open_ended_answers(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'value': 'This is my answer.'
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q1']['value'] == 'This is my answer.'

    def test_first_level_open_ended_answer_must_have_correct_key(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'values': 'This is my answer.'
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Additional properties are not allowed (u\'values\' was unexpected)'

    def test_first_level_open_ended_answer_must_be_of_correct_type(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'value': 12345
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '12345 is not of type \'string\''

    def test_first_level_open_ended_answer_not_expecting_more_nested_data(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q1'] = {
            'value': {
                'question': {
                    'value': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '{u\'question\': {u\'value\': u\'This is my answer.\'}} is not of type \'string\''

    def test_second_level_answers(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': {
                    'value': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q7']['value']['question']['value'] == 'This is my answer.'

    def test_second_level_open_ended_answer_must_have_correct_key(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'questions': {
                    'value': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Additional properties are not allowed (u\'questions\' was unexpected)'

    def test_third_level_open_ended_answer_must_have_correct_key(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': {
                    'values': 'This is my answer.'
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Additional properties are not allowed (u\'values\' was unexpected)'

    def test_second_level_open_ended_answer_must_have_correct_type(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': 'This is my answer'
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'u\'This is my answer\' is not of type \'object\''

    def test_third_level_open_ended_answer_must_have_correct_type(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q7'] = {
            'value': {
                'question': {
                    'value': True
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'True is not of type \'string\''

    def test_uploader_metadata(self, app, user, project_public, draft_registration_prereg, payload, url_draft_registrations):
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
                        'sha256': binascii.hexlify(sha256)
                    }]
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q7']['value']['uploader']['value'] == 'Screen Shot 2016-03-30 at 7.02.05 PM.png'

    def test_uploader_metadata_incorrect_key(self, app, user, project_public, draft_registration_prereg, payload, url_draft_registrations):
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
                        'sha256': binascii.hexlify(sha256)
                    }]
                }
            }
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Additional properties are not allowed (u\'selectedFileNames\' was unexpected)'

    def test_multiple_choice_questions_incorrect_choice(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q15'] = {
            'value': 'This is my answer.'
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert (res.json['errors'][0]['detail'] == 'u\'This is my answer.\' is not one of [u\'No blinding is involved in this study.\', '
                                                      'u\'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.\', '
                                                      'u\'Research personnel who interact directly with the study subjects (either human or non-human subjects) will not be aware of the assigned treatments.\', '
                                                      'u\'Research personnel who analyze the data collected from the study are not aware of the treatment applied to any given group.\']')

    def test_multiple_choice_questions(self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata']['q15'] = {
            'value': 'No blinding is involved in this study.'
        }
        res = app.put_json_api(url_draft_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_metadata']['q15']['value'] == 'No blinding is involved in this study.'
