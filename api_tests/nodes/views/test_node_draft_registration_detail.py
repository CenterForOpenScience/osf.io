
from nose.tools import *  # flake8: noqa

from modularodm import Q
from framework.auth.core import Auth
from website.models import MetaSchema
from api.base.settings.defaults import API_BASE
from website.settings import PREREG_ADMIN_TAG
from website.project.model import ensure_schemas
from test_node_draft_registration_list import DraftRegistrationTestCase

from tests.factories import (
    ProjectFactory,
    DraftRegistrationFactory,
    AuthUserFactory
)


class TestDraftRegistrationDetail(DraftRegistrationTestCase):

    def setUp(self):
        super(TestDraftRegistrationDetail, self).setUp()
        ensure_schemas()

        schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', 2)
        )

        self.draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            branched_from=self.public_project
        )
        self.other_project = ProjectFactory(creator=self.user)
        self.url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.draft_registration._id)

    def test_admin_can_view_draft(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(data['attributes']['registration_supplement'], 'OSF-Standard Pre-Data Collection Registration')
        assert_equal(data['id'], self.draft_registration._id)
        assert_equal(data['attributes']['registration_metadata'], {})

    def test_read_only_contributor_cannot_view_draft(self):
        res = self.app.get(self.url, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_write_contributor_cannot_view_draft(self):
        res = self.app.get(self.url, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_non_contributor_cannot_view_draft(self):
        res = self.app.get(self.url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_view_draft(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_draft_must_be_branched_from_node_in_kwargs(self):
        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.other_project._id, self.draft_registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors'][0]
        assert_equal(errors['detail'], 'This draft registration is not created from the given node.')

    def test_reviewer_can_see_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()
        res = self.app.get(self.url, auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(data['attributes']['registration_supplement'], 'OSF-Standard Pre-Data Collection Registration')
        assert_equal(data['id'], self.draft_registration._id)
        assert_equal(data['attributes']['registration_metadata'], {})


class TestDraftRegistrationUpdate(DraftRegistrationTestCase):

    def setUp(self):
        super(TestDraftRegistrationUpdate, self).setUp()
        ensure_schemas()

        schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', 2)
        )

        self.draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            branched_from=self.public_project
        )

        self.prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )

        self.prereg_draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=self.prereg_schema,
            branched_from=self.public_project
        )

        self.registration_metadata = self.prereg_metadata(self.prereg_draft_registration, is_reviewer=False)


        self.other_project = ProjectFactory(creator=self.user)
        self.url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.draft_registration._id)

        self.payload = {
            "data": {
                "id": self.draft_registration._id,
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {
                        "datacompletion": {
                            "value": "No, data collection has not begun"
                        },
                        "looked": {
                            "value": "No"
                        },
                        "comments": {
                            "value": "This is my first registration."
                        }
                    }
                }
            }
        }

    def test_id_required_in_payload(self):
        payload = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {}
                }
            }
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors'][0]
        assert_equal(errors['source']['pointer'], '/data/id')
        assert_equal(errors['detail'], 'This field may not be null.')

    def test_admin_can_update_draft(self):
        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(data['attributes']['registration_supplement'], 'OSF-Standard Pre-Data Collection Registration')
        assert_equal(data['attributes']['registration_metadata'], self.payload['data']['attributes']['registration_metadata'])

    def test_draft_must_be_branched_from_node(self):
        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.other_project._id, self.draft_registration._id)
        res = self.app.put_json_api(url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors'][0]
        assert_equal(errors['detail'], 'This draft registration is not created from the given node.')

    def test_read_only_contributor_cannot_update_draft(self):
        res = self.app.put_json_api(self.url, self.payload, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_write_contributor_cannot_update_draft(self):
        res = self.app.put_json_api(self.url, self.payload, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_non_contributor_cannot_update_draft(self):
        res = self.app.put_json_api(self.url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_update_draft(self):
        res = self.app.put_json_api(self.url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_registration_metadata_must_be_supplied(self):
        self.payload['data']['attributes'] = {}

        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['source']['pointer'], '/data/attributes/registration_metadata')
        assert_equal(errors['detail'], 'This field is required.')

    def test_registration_metadata_must_be_a_dictionary(self):
        self.payload['data']['attributes']['registration_metadata'] = 'Registration data'

        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['source']['pointer'], '/data/attributes/registration_metadata')
        assert_equal(errors['detail'], 'Expected a dictionary of items but got type "unicode".')

    def test_registration_metadata_question_values_must_be_dictionaries(self):
        self.payload['data']['attributes']['registration_metadata']['datacompletion'] = 'No, data collection has not begun'

        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "u'No, data collection has not begun' is not of type 'object'")

    def test_registration_metadata_question_keys_must_be_value(self):
        self.payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            "incorrect_key": "No, data collection has not begun"
        }

        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "Additional properties are not allowed (u'incorrect_key' was unexpected)")

    def test_question_in_registration_metadata_must_be_in_schema(self):
        self.payload['data']['attributes']['registration_metadata']['q11'] = {
            "value": "No, data collection has not begun"
        }

        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "Additional properties are not allowed (u'q11' was unexpected)")

    def test_multiple_choice_question_value_must_match_value_in_schema(self):
        self.payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            "value": "Nope, data collection has not begun"
        }

        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "u'Nope, data collection has not begun' is not one of [u'No, data collection has not begun', u'Yes, data collection is underway or complete']")

    def test_cannot_update_registration_schema(self):
        self.payload['data']['attributes']['registration_supplement'] = 'Open-Ended Registration'
        res = self.app.put_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['registration_supplement'], 'OSF-Standard Pre-Data Collection Registration')

    def test_required_metaschema_questions_not_required_on_update(self):

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.prereg_draft_registration._id)

        del self.registration_metadata['q1']
        self.prereg_draft_registration.registration_metadata = self.registration_metadata
        self.prereg_draft_registration.save()

        payload = {
            "data": {
                "id": self.prereg_draft_registration._id,
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {
                        'q2': {
                            'value': 'New response'
                        }
                    }
                }
            }
        }

        res = self.app.put_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['registration_metadata']['q2']['value'], 'New response')
        assert_not_in('q1', res.json['data']['attributes']['registration_metadata'])

    def test_reviewer_can_update_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            "data": {
                "id": self.prereg_draft_registration._id,
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {
                        'q2': {
                            'comments': [{'value': 'This is incomplete.'}]
                        }
                    }
                }
            }
        }

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.prereg_draft_registration._id)


        res = self.app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['registration_metadata']['q2']['comments'][0]['value'], 'This is incomplete.')
        assert_not_in('q1', res.json['data']['attributes']['registration_metadata'])

    def test_reviewer_can_only_update_comment_fields_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            "data": {
                "id": self.prereg_draft_registration._id,
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {
                        'q2': {
                            'value': 'Test response'
                        }
                    }
                }
            }
        }

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.prereg_draft_registration._id)

        res = self.app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Additional properties are not allowed (u'value' was unexpected)")

    def test_reviewer_can_update_nested_comment_fields_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            "data": {
                "id": self.prereg_draft_registration._id,
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {
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

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.prereg_draft_registration._id)

        res = self.app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['registration_metadata']['q7']['value']['question']['comments'][0]['value'], 'Add some clarity here.')

    def test_reviewer_cannot_update_nested_value_fields_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()

        payload = {
            "data": {
                "id": self.prereg_draft_registration._id,
                "type": "draft_registrations",
                "attributes": {
                    "registration_metadata": {
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

        url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.prereg_draft_registration._id)

        res = self.app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Additional properties are not allowed (u'value' was unexpected)")


class TestDraftRegistrationDelete(DraftRegistrationTestCase):
    def setUp(self):
        super(TestDraftRegistrationDelete, self).setUp()
        ensure_schemas()

        schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', 2)
        )

        self.draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            branched_from=self.public_project
        )
        self.other_project = ProjectFactory(creator=self.user)
        self.url = '/{}nodes/{}/draft_registrations/{}/'.format(API_BASE, self.public_project._id, self.draft_registration._id)

    def test_admin_can_delete_draft(self):
        res = self.app.delete_json_api(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_read_only_contributor_cannot_delete_draft(self):
        res = self.app.delete_json_api(self.url, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_write_contributor_cannot_delete_draft(self):
        res = self.app.delete_json_api(self.url, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_non_contributor_cannot_delete_draft(self):
        res = self.app.delete_json_api(self.url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_delete_draft(self):
        res = self.app.delete_json_api(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_draft_that_has_been_registered_cannot_be_deleted(self):
        self.draft_registration.register(auth=Auth(self.user), save=True)
        res = self.app.delete_json_api(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'This draft has already been registered and cannot be modified.')

    def test_reviewer_cannot_delete_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()

        res = self.app.delete_json_api(self.url, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')