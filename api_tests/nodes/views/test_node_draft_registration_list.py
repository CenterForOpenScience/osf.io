from nose.tools import *  # flake8: noqa

from website.project.model import ensure_schemas
from website.models import MetaSchema
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from website.project.metadata.utils import create_jsonschema_from_metaschema
from modularodm import Q
from website.util import permissions
from website.settings import PREREG_ADMIN_TAG

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CollectionFactory,
    DraftRegistrationFactory
)

class DraftRegistrationTestCase(ApiTestCase):

    def setUp(self):
        super(DraftRegistrationTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.read_only_user = AuthUserFactory()
        self.read_write_user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.read_only_user, permissions=[permissions.READ])
        self.public_project.add_contributor(self.read_write_user, permissions=[permissions.WRITE])
        self.public_project.save()

    def prereg_metadata(self, draft):
        test_metadata = {}
        json_schema = create_jsonschema_from_metaschema(draft.registration_schema.schema)

        for key, value in json_schema['properties'].iteritems():
            response = 'Test response'
            if value['properties']['value'].get('enum'):
                response = value['properties']['value']['enum'][0]

            if value['properties']['value'].get('properties'):
                response = {'question': {'value': 'Test Response'}}

            test_metadata[key] = {'value': response}
        return test_metadata


class TestDraftRegistrationList(DraftRegistrationTestCase):

    def setUp(self):
        super(TestDraftRegistrationList, self).setUp()
        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended Registration') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )

        self.draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=self.schema,
            branched_from=self.public_project
        )

        self.url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, self.public_project._id)

    def test_admin_can_view_draft_list(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['registration_supplement'], self.schema._id)
        assert_equal(data[0]['id'], self.draft_registration._id)
        assert_equal(data[0]['attributes']['registration_metadata'], {})

    def test_read_only_contributor_cannot_view_draft_list(self):
        res = self.app.get(self.url, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_write_contributor_cannot_view_draft_list(self):
        res = self.app.get(self.url, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_non_contributor_cannot_view_draft_list(self):
        res = self.app.get(self.url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_view_draft_list(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_draft_with_registered_node_does_not_show_up_in_draft_list(self):
        reg = RegistrationFactory(project = self.public_project)
        self.draft_registration.registered_node = reg
        self.draft_registration.save()
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 0)

    def test_draft_with_deleted_registered_node_shows_up_in_draft_list(self):
        reg = RegistrationFactory(project=self.public_project)
        self.draft_registration.registered_node = reg
        self.draft_registration.save()
        reg.is_deleted = True
        reg.save()
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['registration_supplement'], self.schema._id)
        assert_equal(data[0]['id'], self.draft_registration._id)
        assert_equal(data[0]['attributes']['registration_metadata'], {})


class TestDraftRegistrationCreate(DraftRegistrationTestCase):
    def setUp(self):
        super(TestDraftRegistrationCreate, self).setUp()
        self.url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, self.public_project._id)
        ensure_schemas()
        self.open_ended_metaschema = MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended Registration') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )

        self.payload = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_supplement": self.open_ended_metaschema._id
                }
            }
        }

    def test_type_is_draft_registrations(self):
        draft_data = {
            "data": {
                "type": "nodes",
                "attributes": {
                    "registration_supplement": self.open_ended_metaschema._id
                }
            }
        }
        res = self.app.post_json_api(self.url, draft_data, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(errors['detail'], "Resource identifier does not match server endpoint.")
        assert_equal(res.status_code, 409)

    def test_admin_can_create_draft(self):
        url = '/{}nodes/{}/draft_registrations/?embed=branched_from&embed=initiator'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(data['attributes']['registration_supplement'], self.open_ended_metaschema._id)
        assert_equal(data['attributes']['registration_metadata'], {})
        assert_equal(data['embeds']['branched_from']['data']['id'], self.public_project._id)
        assert_equal(data['embeds']['initiator']['data']['id'], self.user._id)

    def test_write_only_contributor_cannot_create_draft(self):
        assert_in(self.read_write_user._id, self.public_project.contributors)
        res = self.app.post_json_api(self.url, self.payload, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_create_draft(self):
        assert_in(self.read_only_user._id, self.public_project.contributors)
        res = self.app.post_json_api(self.url, self.payload, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_non_authenticated_user_cannot_create_draft(self):
        res = self.app.post_json_api(self.url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_logged_in_non_contributor_cannot_create_draft(self):
        res = self.app.post_json_api(self.url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_registration_supplement_not_found(self):
        draft_data = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_supplement": "Invalid schema"
                }
            }
        }
        res = self.app.post_json_api(self.url, draft_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_registration_supplement_must_be_active_metaschema(self):
        schema =  MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended Registration') &
            Q('schema_version', 'eq', 1)
        )
        draft_data = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_supplement": schema._id
                }
            }
        }
        res = self.app.post_json_api(self.url, draft_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Registration supplement must be an active schema.')

    def test_cannot_create_draft_from_a_registration(self):
        registration = RegistrationFactory(project=self.public_project, creator=self.user)
        url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, registration._id)
        res = self.app.post_json_api(url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_registration_supplement_must_be_supplied(self):
        draft_data = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                }
            }
        }
        res = self.app.post_json_api(self.url, draft_data, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], 'This field is required.')
        assert_equal(errors['source']['pointer'], '/data/attributes/registration_supplement')

    def test_cannot_create_draft_from_deleted_node(self):
        self.public_project.is_deleted = True
        self.public_project.save()
        res = self.app.post_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        assert_equal(res.json['errors'][0]['detail'], 'The requested node is no longer available.')

    def test_cannot_create_draft_from_collection(self):
        collection = CollectionFactory(creator=self.user)
        url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, collection._id)
        res = self.app.post_json_api(url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_required_metaschema_questions_not_required_on_post(self):
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )

        prereg_draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema._id,
            branched_from=self.public_project
        )

        url = '/{}nodes/{}/draft_registrations/?embed=initiator&embed=branched_from'.format(API_BASE, self.public_project._id)

        registration_metadata = self.prereg_metadata(prereg_draft_registration)
        del registration_metadata['q1']
        prereg_draft_registration.registration_metadata = registration_metadata
        prereg_draft_registration.save()

        payload = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_supplement": prereg_schema._id,
                    "registration_metadata": registration_metadata
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(res.json['data']['attributes']['registration_metadata']['q2']['value'], 'Test response')
        assert_equal(data['attributes']['registration_supplement'], prereg_schema._id)
        assert_equal(data['embeds']['branched_from']['data']['id'], self.public_project._id)
        assert_equal(data['embeds']['initiator']['data']['id'], self.user._id)

    def test_registration_metadata_must_be_a_dictionary(self):
        self.payload['data']['attributes']['registration_metadata'] = 'Registration data'

        res = self.app.post_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['source']['pointer'], '/data/attributes/registration_metadata')
        assert_equal(errors['detail'], 'Expected a dictionary of items but got type "unicode".')

    def test_registration_metadata_question_values_must_be_dictionaries(self):
        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )
        self.payload['data']['attributes']['registration_supplement'] = self.schema._id
        self.payload['data']['attributes']['registration_metadata'] = {}
        self.payload['data']['attributes']['registration_metadata']['datacompletion'] = 'No, data collection has not begun'

        res = self.app.post_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "u'No, data collection has not begun' is not of type 'object'")

    def test_registration_metadata_question_keys_must_be_value(self):
        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )
        self.payload['data']['attributes']['registration_supplement'] = self.schema._id
        self.payload['data']['attributes']['registration_metadata'] = {}
        self.payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            "incorrect_key": "No, data collection has not begun"
        }

        res = self.app.post_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "Additional properties are not allowed (u'incorrect_key' was unexpected)")

    def test_question_in_registration_metadata_must_be_in_schema(self):
        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )
        self.payload['data']['attributes']['registration_supplement'] = self.schema._id
        self.payload['data']['attributes']['registration_metadata'] = {}
        self.payload['data']['attributes']['registration_metadata']['q11'] = {
            "value": "No, data collection has not begun"
        }

        res = self.app.post_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "Additional properties are not allowed (u'q11' was unexpected)")

    def test_multiple_choice_question_value_must_match_value_in_schema(self):
        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )

        self.payload['data']['attributes']['registration_supplement'] = self.schema._id
        self.payload['data']['attributes']['registration_metadata'] = {}
        self.payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            "value": "Nope, data collection has not begun"
        }

        res = self.app.post_json_api(self.url, self.payload, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(res.status_code, 400)
        assert_equal(errors['detail'], "u'Nope, data collection has not begun' is not one of [u'No, data collection has not begun', u'Yes, data collection is underway or complete']")

    def test_reviewer_cannot_create_draft_registration(self):
        user = AuthUserFactory()
        user.system_tags.append(PREREG_ADMIN_TAG)
        user.save()

        assert_in(self.read_only_user._id, self.public_project.contributors)
        res = self.app.post_json_api(self.url, self.payload, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
