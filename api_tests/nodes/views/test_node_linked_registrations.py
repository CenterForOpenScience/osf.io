from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from tests.base import ApiTestCase
from tests.factories import (
    AuthUserFactory,
    NodeFactory,
    RegistrationFactory,
)


class LinkedRegistrationsTestCase(ApiTestCase):

    def setUp(self):
        super(LinkedRegistrationsTestCase, self).setUp()
        self.registration = RegistrationFactory(is_public=True)

        self.public_node = NodeFactory(is_public=True)
        self.public_node.add_pointer(self.registration, auth=Auth(self.public_node.creator))
        self.public_node.save()

        self.admin_contributor = AuthUserFactory()
        self.rw_contributor = AuthUserFactory()
        self.read_contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.private_node = NodeFactory(creator=self.admin_contributor)
        self.private_node.add_contributor(self.rw_contributor, auth=Auth(self.admin_contributor))
        self.private_node.add_contributor(self.read_contributor, permissions=['read'], auth=Auth(self.admin_contributor))
        self.private_node.add_pointer(self.registration, auth=Auth(self.admin_contributor))
        self.private_node.save()


class TestNodeLinkedRegistrationsList(LinkedRegistrationsTestCase):

    def setUp(self):
        super(TestNodeLinkedRegistrationsList, self).setUp()

    def make_request(self, node_id=None, auth=None, expect_errors=False):
        url = '/{}nodes/{}/linked_registrations/'.format(API_BASE, node_id)
        if auth:
            return self.app.get(url, auth=auth, expect_errors=expect_errors)
        return self.app.get(url, expect_errors=expect_errors)

    def test_public_node_unauthenticated_user_can_view_linked_registrations(self):
        res = self.make_request(node_id=self.public_node._id)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_admin_contributor_can_view_linked_registrations(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_rw_contributor_can_view_linked_registrations(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.rw_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_read_contributor_can_view_linked_registrations(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.read_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_non_contributor_cannot_view_linked_registrations(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_unauthenticated_user_cannot_view_linked_registrations(self):
        res = self.make_request(node_id=self.private_node._id, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


class TestNodeLinkedRegistrationsRelationshipRetrieve(LinkedRegistrationsTestCase):

    def setUp(self):
        super(TestNodeLinkedRegistrationsRelationshipRetrieve, self).setUp()

    def make_request(self, node_id=None, auth=None, expect_errors=False):
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(API_BASE, node_id)
        if auth:
            return self.app.get(url, auth=auth, expect_errors=expect_errors)
        return self.app.get(url, expect_errors=expect_errors)

    def test_public_node_unauthenticated_user_can_view_linked_registrations_relationship(self):
        res = self.make_request(node_id=self.public_node._id)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_admin_contributor_can_view_linked_registrations_relationship(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_rw_contributor_can_view_linked_registrations_relationship(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.rw_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_read_contributor_can_view_linked_registrations_relationship(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.read_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.registration._id)

    def test_private_node_non_contributor_cannot_view_linked_registrations_relationship(self):
        res = self.make_request(node_id=self.private_node._id, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_unauthenticated_user_cannot_view_linked_registrations_relationship(self):
        res = self.make_request(node_id=self.private_node._id, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


class TestNodeLinkedRegistrationsRelationshipCreate(LinkedRegistrationsTestCase):

    def setUp(self):
        super(TestNodeLinkedRegistrationsRelationshipCreate, self).setUp()

    def make_payload(self, registration_id=None):
        return {
            'data': [{
                'type': 'linked_registrations',
                'id': registration_id
            }]
        }

    def make_request(self, node_id=None, auth=None, reg_id=None, expect_errors=False):
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(API_BASE, node_id)
        if auth:
            return self.app.post_json_api(url, self.make_payload(registration_id=reg_id), auth=auth, expect_errors=expect_errors)
        return self.app.post_json_api(url, self.make_payload(registration_id=reg_id), expect_errors=expect_errors)

    def test_admin_contributor_can_create_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.admin_contributor.auth
        )
        assert_equal(res.status_code, 201)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_in(registration._id, linked_registrations)

    def test_rw_contributor_can_create_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.rw_contributor.auth
        )
        assert_equal(res.status_code, 201)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_in(registration._id, linked_registrations)

    def test_read_contributor_cannot_create_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.read_contributor.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_non_contributor_cannot_create_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.non_contributor.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_unauthenticated_user_cannot_create_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_cannot_create_linked_registrations_relationship_invalid_registration_guid(self):
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id='abcde',
            auth=self.admin_contributor.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Node with id "abcde" was not found')

    def test_create_linked_registrations_relationship_registration_already_in_linked_registrations_returns_no_content(self):
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=self.registration._id,
            auth=self.admin_contributor.auth
        )
        assert_equal(res.status_code, 204)

    def test_can_create_linked_registration_relationship_to_private_registration_if_admin(self):
        registration = RegistrationFactory(creator=self.admin_contributor)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.admin_contributor.auth
        )
        assert_equal(res.status_code, 201)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_in(registration._id, linked_registrations)

    def test_can_create_linked_registration_relationship_to_private_registration_if_rw(self):
        registration = RegistrationFactory()
        registration.add_contributor(self.admin_contributor, auth=Auth(registration.creator))
        registration.save()
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.admin_contributor.auth
        )
        assert_equal(res.status_code, 201)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_in(registration._id, linked_registrations)

    def test_can_create_linked_registration_relationship_to_private_registration_if_read_only(self):
        registration = RegistrationFactory()
        registration.add_contributor(self.admin_contributor, auth=Auth(registration.creator), permissions=['read'])
        registration.save()
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.admin_contributor.auth
        )
        assert_equal(res.status_code, 201)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_in(registration._id, linked_registrations)

    def test_cannot_create_linked_registration_relationship_to_private_registration_if_non_contributor(self):
        registration = RegistrationFactory()
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.admin_contributor.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')


class TestNodeLinkedRegistrationsRelationshipUpdate(LinkedRegistrationsTestCase):

    def setUp(self):
        super(TestNodeLinkedRegistrationsRelationshipUpdate, self).setUp()

    def make_payload(self, registration_id=None):
        return {
            'data': [{
                'type': 'linked_registrations',
                'id': registration_id
            }]
        }

    def make_request(self, node_id=None, auth=None, reg_id=None, expect_errors=False):
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(API_BASE, node_id)
        if auth:
            return self.app.put_json_api(url, self.make_payload(registration_id=reg_id), auth=auth, expect_errors=expect_errors)
        return self.app.put_json_api(url, self.make_payload(registration_id=reg_id), expect_errors=expect_errors)

    def test_admin_contributor_can_update_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.admin_contributor.auth
        )
        assert_equal(res.status_code, 200)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_not_in(self.registration._id, linked_registrations)
        assert_in(registration._id, linked_registrations)

    def test_rw_contributor_can_update_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.rw_contributor.auth
        )
        assert_equal(res.status_code, 200)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_not_in(self.registration._id, linked_registrations)
        assert_in(registration._id, linked_registrations)

    def test_read_contributor_cannot_update_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.read_contributor.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_non_contributor_cannot_update_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            auth=self.non_contributor.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_unauthenticated_user_cannot_update_linked_registrations_relationship(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_empty_payload_removes_existing_linked_registrations(self):
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(API_BASE, self.private_node._id)
        res = self.app.put_json_api(url, {}, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        linked_registrations = [r['id'] for r in res.json['data']]
        assert_not_in(self.registration._id, linked_registrations)


class TestNodeLinkedRegistrationsRelationshipDelete(LinkedRegistrationsTestCase):

    def setUp(self):
        super(TestNodeLinkedRegistrationsRelationshipDelete, self).setUp()

    def make_payload(self, registration_id=None):
        return {
            'data': [{
                'type': 'linked_registrations',
                'id': registration_id
            }]
        }

    def make_request(self, node_id=None, auth=None, reg_id=None, expect_errors=False):
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(API_BASE, node_id)
        if auth:
            return self.app.delete_json_api(url, self.make_payload(reg_id), auth=auth, expect_errors=expect_errors)
        return self.app.delete_json_api(url, self.make_payload(reg_id), expect_errors=expect_errors)

    def test_admin_contributor_can_delete_linked_registrations_relationship(self):
        res = self.make_request(
            node_id=self.private_node._id,
            auth=self.admin_contributor.auth,
            reg_id=self.registration._id
        )
        assert_equal(res.status_code, 204)

    def test_rw_contributor_can_delete_linked_registrations_relationship(self):
        res = self.make_request(
            node_id=self.private_node._id,
            auth=self.rw_contributor.auth,
            reg_id=self.registration._id
        )
        assert_equal(res.status_code, 204)

    def test_read_contributor_cannot_delete_linked_registrations_relationship(self):
        res = self.make_request(
            node_id=self.private_node._id,
            auth=self.read_contributor.auth,
            reg_id=self.registration._id,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_non_contributor_cannot_delete_linked_registrations_relationship(self):
        res = self.make_request(
            node_id=self.private_node._id,
            auth=self.non_contributor.auth,
            reg_id=self.registration._id,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_unauthenticated_user_cannot_delete_linked_registrations_relationship(self):
        res = self.make_request(
            node_id=self.private_node._id,
            reg_id=self.registration._id,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_cannot_delete_linked_registrations_relationship_invalid_registration_guid(self):
        res = self.make_request(
            node_id=self.private_node._id,
            auth=self.admin_contributor.auth,
            reg_id='abcde',
            expect_errors=True
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Pointer with id "abcde" not found in pointers list')

    def test_cannot_delete_linked_registrations_relationship_registration_not_in_linked_registrations(self):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            node_id=self.private_node._id,
            auth=self.admin_contributor.auth,
            reg_id=registration._id,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Pointer with id "{}" not found in pointers list'.format(
            registration._id
        ))
