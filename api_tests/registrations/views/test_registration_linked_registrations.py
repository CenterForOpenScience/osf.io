from unittest import mock

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    RegistrationFactory,
    DraftRegistrationFactory,
)
from osf.utils.permissions import READ
from tests.base import ApiTestCase, get_default_metaschema


class LinkedRegistrationsTestCase(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.mock_archive = mock.patch('website.archiver.tasks.archive')

        self.non_contributor = AuthUserFactory()
        self.read_contributor = AuthUserFactory()
        self.rw_contributor = AuthUserFactory()
        self.admin_contributor = AuthUserFactory()

        self.public_linked_registration = RegistrationFactory(
            is_public=True, creator=self.rw_contributor)
        self.private_linked_registration = RegistrationFactory(
            is_public=False, creator=self.rw_contributor)

        self.mock_archive.start()

        public_node = NodeFactory(
            creator=self.admin_contributor,
            is_public=True)
        public_node.add_contributor(
            self.rw_contributor, auth=Auth(self.admin_contributor))
        public_node.add_contributor(
            self.read_contributor,
            permissions=READ,
            auth=Auth(self.admin_contributor))
        public_node.add_pointer(
            self.public_linked_registration,
            auth=Auth(self.admin_contributor))
        public_node.add_pointer(
            self.private_linked_registration,
            auth=Auth(self.rw_contributor))
        public_node.save()
        draft_reg = DraftRegistrationFactory(
            branched_from=public_node,
            initiator=self.admin_contributor
        )
        self.public_registration = public_node.register_node(
            get_default_metaschema(), Auth(self.admin_contributor), draft_reg, None)
        self.public_registration.is_public = True
        self.public_registration.save()

        private_node = NodeFactory(creator=self.admin_contributor)
        private_node.add_contributor(
            self.rw_contributor,
            auth=Auth(self.admin_contributor))
        private_node.add_contributor(
            self.read_contributor,
            permissions=READ,
            auth=Auth(self.admin_contributor))
        private_node.add_pointer(
            self.public_linked_registration,
            auth=Auth(self.admin_contributor))
        private_node.add_pointer(
            self.private_linked_registration,
            auth=Auth(self.rw_contributor))
        private_node.save()
        draft_reg = DraftRegistrationFactory(
            branched_from=private_node,
            initiator=self.admin_contributor
        )
        self.private_registration = private_node.register_node(
            get_default_metaschema(), Auth(self.admin_contributor), draft_reg, None)

    def tearDown(self):
        super().tearDown()
        self.mock_archive.stop()


class TestRegistrationLinkedRegistrationsList(LinkedRegistrationsTestCase):

    def setUp(self):
        super().setUp()

    def make_request(
            self, registration_id=None, auth=None, expect_errors=False):
        url = '/{}registrations/{}/linked_registrations/'.format(
            API_BASE, registration_id)
        if auth:
            return self.app.get(url, auth=auth, expect_errors=expect_errors)
        return self.app.get(url, expect_errors=expect_errors)

    def test_unauthenticated_can_view_public_registration_linked_registrations(
            self):
        res = self.make_request(registration_id=self.public_registration._id)
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids

    def test_admin_can_view_private_registration_linked_registrations(self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.admin_contributor.auth
        )
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids

    def test_rw_contributor_can_view_private_registration_linked_registrations(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.rw_contributor.auth
        )
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id in linked_registration_ids

    def test_read_only_contributor_can_view_private_registration_linked_registrations(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.read_contributor.auth
        )
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids

    def test_non_contributor_cannot_view_private_registration_linked_registrations(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.non_contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_unauthenticated_cannot_view_private_registration_linked_registrations(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'


class TestRegistrationsLinkedRegistrationsRelationship(
        LinkedRegistrationsTestCase):

    def setUp(self):
        super().setUp()
        self.public_url = '/{}registrations/{}/relationships/linked_registrations/'.format(
            API_BASE, self.public_registration._id)

    def make_request(
            self, registration_id=None, auth=None, expect_errors=False, version=None):
        url = '/{}registrations/{}/relationships/linked_registrations/'.format(
            API_BASE, registration_id)
        if version:
            url = f'{url}?version={version}'
        if auth:
            return self.app.get(url, auth=auth, expect_errors=expect_errors)
        return self.app.get(url, expect_errors=expect_errors)

    def test_public_registration_unauthenticated_user_can_view_linked_registrations_relationship(
            self):
        res = self.make_request(registration_id=self.public_registration._id)
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids
        assert res.json['data'][0]['type'] == 'linked_registrations'

    def test_public_registration_unauthenticated_user_can_view_linked_registrations_relationship_2_13(
            self):
        res = self.make_request(registration_id=self.public_registration._id, version='2.13')
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids
        assert res.json['data'][0]['type'] == 'registrations'

    def test_private_registration_admin_contributor_can_view_linked_registrations_relationship(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.admin_contributor.auth
        )
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids

    def test_private_registration_rw_contributor_can_view_linked_registrations_relationship(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.rw_contributor.auth
        )
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id in linked_registration_ids

    def test_private_registration_read_contributor_can_view_linked_registrations_relationship(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.read_contributor.auth
        )
        assert res.status_code == 200
        linked_registration_ids = [r['id'] for r in res.json['data']]
        assert self.public_linked_registration._id in linked_registration_ids
        assert self.private_linked_registration._id not in linked_registration_ids

    def test_private_registration_non_contributor_cannot_view_linked_registrations_relationship(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            auth=self.non_contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_private_registration_unauthenticated_user_cannot_view_linked_registrations_relationship(
            self):
        res = self.make_request(
            registration_id=self.private_registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

    def test_cannot_create_linked_registrations_relationship(self):
        res = self.app.post_json_api(
            self.public_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert res.status_code == 405

    def test_cannot_update_linked_registrations_relationship(self):
        res = self.app.put_json_api(
            self.public_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert res.status_code == 405

    def test_cannot_delete_linked_registrations_relationship(self):
        res = self.app.delete_json_api(
            self.public_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert res.status_code == 405
