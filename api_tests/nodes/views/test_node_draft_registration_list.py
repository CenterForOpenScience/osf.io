from nose.tools import *  # flake8: noqa

from website.project.model import ensure_schemas
from website.models import MetaSchema
from modularodm import Q
from framework.auth.core import Auth
from website.util import permissions

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
        from api.base.utils import create_json_schema_for_metaschema
        test_metadata = {}
        json_schema = create_json_schema_for_metaschema(draft)

        for key, value in json_schema['properties'].iteritems():
            response = 'Test response'
            if value['properties']['value'].get('enum'):
                response = value['properties']['value']['enum'][0]

            test_metadata[key] = {'value': response}
        return test_metadata

class TestDraftRegistrationList(DraftRegistrationTestCase):

    def setUp(self):
        super(TestDraftRegistrationList, self).setUp()
        ensure_schemas()
        schema = MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended Registration') &
            Q('schema_version', 'eq', 2)
        )

        self.draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            branched_from=self.public_project
        )

        self.url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, self.public_project._id)

    def test_admin_can_view_draft_list(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['registration_form'], 'Open-Ended Registration')
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
        self.draft_registration.register(auth=Auth(self.user), save=True)
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 0)

    def test_draft_with_deleted_registered_node_shows_up_in_draft_list(self):
        registration = self.draft_registration.register(auth=Auth(self.user), save=True)
        registration.is_deleted = True
        registration.save()
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['registration_form'], 'Open-Ended Registration')
        assert_equal(data[0]['id'], self.draft_registration._id)
        assert_equal(data[0]['attributes']['registration_metadata'], {})


class TestDraftRegistrationCreate(DraftRegistrationTestCase):
    def setUp(self):
        super(TestDraftRegistrationCreate, self).setUp()
        self.url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, self.public_project._id)
        ensure_schemas()

        self.draft_data = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_form": "Open-Ended Registration"
                }
            }
        }

    def test_type_is_draft_registrations(self):
        draft_data = {
            "data": {
                "type": "nodes",
                "attributes": {
                    "registration_form": "Open-Ended Registration"
                }
            }
        }
        res = self.app.post_json_api(self.url, draft_data, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors'][0]
        assert_equal(errors['detail'], "Resource identifier does not match server endpoint.")
        assert_equal(res.status_code, 409)

    def test_admin_can_create_draft(self):
        url = '/{}nodes/{}/draft_registrations/?embed=branched_from&embed=initiator'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, self.draft_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(data['attributes']['registration_form'], 'Open-Ended Registration')
        assert_equal(data['attributes']['registration_metadata'], {})
        assert_equal(data['embeds']['branched_from']['data']['id'], self.public_project._id)
        assert_equal(data['embeds']['initiator']['data']['id'], self.user._id)

    def test_write_only_contributor_cannot_create_draft(self):
        assert_in(self.read_write_user._id, self.public_project.contributors)
        res = self.app.post_json_api(self.url, self.draft_data, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_create_draft(self):
        assert_in(self.read_only_user._id, self.public_project.contributors)
        res = self.app.post_json_api(self.url, self.draft_data, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_non_authenticated_user_cannot_create_draft(self):
        res = self.app.post_json_api(self.url, self.draft_data, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_logged_in_non_contributor_cannot_create_draft(self):
        res = self.app.post_json_api(self.url, self.draft_data, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_registration_form_must_be_one_of_active_schemas(self):
        draft_data = {
            "data": {
                "type": "draft_registrations",
                "attributes": {
                    "registration_form": "Invalid schema"
                }
            }
        }
        res = self.app.post_json_api(self.url, draft_data, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors'][0]
        assert_equal(errors['source']['pointer'], '/data/attributes/registration_form')
        assert_equal(errors['detail'], '"Invalid schema" is not a valid choice.')

    def test_cannot_create_draft_from_a_registration(self):
        registration = RegistrationFactory(project=self.public_project, creator=self.user)
        url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, registration._id)
        res = self.app.post_json_api(url, self.draft_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_registration_form_must_be_supplied(self):
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
        assert_equal(errors['source']['pointer'], '/data/attributes/registration_form')

    def test_cannot_create_draft_from_deleted_node(self):
        self.public_project.is_deleted = True
        self.public_project.save()
        res = self.app.post_json_api(self.url, self.draft_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        assert_equal(res.json['errors'][0]['detail'], 'The requested node is no longer available.')

    def test_cannot_create_draft_from_collection(self):
        collection = CollectionFactory(creator=self.user)
        url = '/{}nodes/{}/draft_registrations/'.format(API_BASE, collection._id)
        res = self.app.post_json_api(url, self.draft_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_required_metaschema_questions_not_required_on_post(self):
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )

        prereg_draft_registration = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema,
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
                    "registration_form": "Prereg Challenge",
                    "registration_metadata": registration_metadata
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(res.json['data']['attributes']['registration_metadata']['q2']['value'], 'Test response')
        assert_equal(data['attributes']['registration_form'], 'Prereg Challenge')
        assert_equal(data['embeds']['branched_from']['data']['id'], self.public_project._id)
        assert_equal(data['embeds']['initiator']['data']['id'], self.user._id)
