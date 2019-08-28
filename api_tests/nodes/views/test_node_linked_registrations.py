import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    OSFGroupFactory,
    RegistrationFactory,
    NodeRelationFactory,
)
from osf.utils.permissions import READ
from rest_framework import exceptions


@pytest.mark.django_db
class LinkedRegistrationsTestCase:

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
    def registration(self):
        return RegistrationFactory(is_public=True)

    @pytest.fixture()
    def node_public(self, registration):
        node_public = NodeFactory(is_public=True)
        node_public.add_pointer(registration, auth=Auth(node_public.creator))
        node_public.save()
        return node_public

    @pytest.fixture()
    def node_private(
            self, user_admin_contrib, user_write_contrib,
            user_read_contrib, registration):
        node_private = NodeFactory(creator=user_admin_contrib)
        node_private.add_contributor(
            user_write_contrib,
            auth=Auth(user_admin_contrib))
        node_private.add_contributor(
            user_read_contrib,
            permissions=READ,
            auth=Auth(user_admin_contrib))
        node_private.add_pointer(registration, auth=Auth(user_admin_contrib))
        return node_private


@pytest.mark.django_db
class TestNodeLinkedRegistrationsList(LinkedRegistrationsTestCase):

    @pytest.fixture()
    def make_request(self, app):
        def request(node_id=None, auth=None, expect_errors=False):
            url = '/{}nodes/{}/linked_registrations/'.format(API_BASE, node_id)
            if auth:
                return app.get(url, auth=auth, expect_errors=expect_errors)
            return app.get(url, expect_errors=expect_errors)
        return request

    def test_view_linked_registrations(
            self, make_request, user_admin_contrib,
            user_write_contrib, user_read_contrib,
            user_non_contrib, registration,
            node_public, node_private):

        #   test_public_node_unauthenticated_user_can_view_linked_registrations
        res = make_request(node_id=node_public._id)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_admin_contributor_can_view_linked_registrations
        res = make_request(
            node_id=node_private._id,
            auth=user_admin_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_rw_contributor_can_view_linked_registrations
        res = make_request(
            node_id=node_private._id,
            auth=user_write_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_read_contributor_can_view_linked_registrations
        res = make_request(
            node_id=node_private._id,
            auth=user_read_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_non_contributor_cannot_view_linked_registrations
        res = make_request(
            node_id=node_private._id,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_private_node_unauthenticated_user_cannot_view_linked_registrations
        res = make_request(node_id=node_private._id, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_osf_group_member_read_can_view_linked_reg
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_private.add_osf_group(group, READ)
        res = make_request(
            node_id=node_private._id,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 200


@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipRetrieve(
        LinkedRegistrationsTestCase):

    @pytest.fixture()
    def make_request(self, app):
        def request(node_id=None, auth=None, expect_errors=False, version=None):
            url = '/{}nodes/{}/relationships/linked_registrations/'.format(
                API_BASE, node_id)
            if version:
                url = '{}?version={}'.format(url, version)
            if auth:
                return app.get(url, auth=auth, expect_errors=expect_errors)
            return app.get(url, expect_errors=expect_errors)
        return request

    def test_can_vew_linked_registrations_relationship(
            self, make_request, registration, user_admin_contrib,
            user_write_contrib, user_read_contrib, user_non_contrib,
            node_public, node_private):

        #   test_public_node_unauthenticated_user_can_view_linked_registrations_relationship
        res = make_request(node_id=node_public._id)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id
        assert res.json['data'][0]['type'] == 'linked_registrations'

        #   test_public_node_unauthenticated_user_can_view_linked_registrations_relationship_2_13
        res = make_request(node_id=node_public._id, version='2.13')
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id
        assert res.json['data'][0]['type'] == 'registrations'

    #   test_private_node_admin_contributor_can_view_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            auth=user_admin_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_rw_contributor_can_view_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            auth=user_write_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_read_contributor_can_view_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            auth=user_read_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    #   test_private_node_non_contributor_cannot_view_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_private_node_unauthenticated_user_cannot_view_linked_registrations_relationship
        res = make_request(node_id=node_private._id, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_osf_group_member_can_view_linked_registration_relationship
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_private.add_osf_group(group, READ)
        res = make_request(
            node_id=node_private._id,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 200


@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipCreate(
        LinkedRegistrationsTestCase):

    @pytest.fixture()
    def make_payload(self):
        def payload(registration_id=None, deprecated_type=True):
            return {
                'data': [{
                    'type': 'linked_registrations' if deprecated_type else 'registrations',
                    'id': registration_id
                }]
            }
        return payload

    @pytest.fixture()
    def make_request(self, app, make_payload):
        def request(node_id=None, auth=None, reg_id=None, expect_errors=False, version=None, deprecated_type=True):
            url = '/{}nodes/{}/relationships/linked_registrations/'.format(
                API_BASE, node_id)
            if version:
                url = '{}?version={}'.format(url, version)
            if auth:
                return app.post_json_api(
                    url,
                    make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                    auth=auth, expect_errors=expect_errors)
            return app.post_json_api(
                url,
                make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                expect_errors=expect_errors)
        return request

    def test_admin_contributor_can_create_linked_registrations_relationship(
            self, make_request, user_admin_contrib, node_private):
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 201
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id in linked_registrations

    def test_admin_contributor_can_create_linked_registrations_relationship_2_13(
            self, make_request, user_admin_contrib, node_private):
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth,
            version='2.13',
            deprecated_type=False,
        )
        assert res.status_code == 201
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id in linked_registrations

    def test_rw_contributor_can_create_linked_registrations_relationship(
            self, make_request, user_write_contrib, node_private):
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_write_contrib.auth
        )
        assert res.status_code == 201
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id in linked_registrations

    def test_cannot_create_linked_registrations_relationship(
            self, app, make_request, user_admin_contrib, user_read_contrib,
            user_non_contrib, node_private, make_payload):

        #   test_read_contributor_cannot_create_linked_registrations_relationship
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_non_contributor_cannot_create_linked_registrations_relationship
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_read_osf_group_mem_cannot_create_linked_registrations_relationship
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_private.add_osf_group(group, READ)
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=group_mem.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_create_linked_registrations_relationship
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_cannot_create_linked_registrations_relationship_invalid_registration_guid
        res = make_request(
            node_id=node_private._id,
            reg_id='abcde',
            auth=user_admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Node with id "abcde" was not found'

    #   test_cannot_create_linked_registration_relationship_to_private_registration_if_non_contributor
        registration = RegistrationFactory()
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_cannot_create_relationship_with_child_registration
        child_reg = RegistrationFactory(creator=user_admin_contrib)
        NodeRelationFactory(child=child_reg, parent=node_private)
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(
            API_BASE, node_private._id)
        data = make_payload(registration_id=child_reg._id)
        res = app.post_json_api(url, data, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Target Node \'{}\' is already a child of \'{}\'.'.format(child_reg._id, node_private._id)

    #   test_cannot_create_link_registration_to_itself
        res = make_request(
            node_id=node_private._id,
            reg_id=node_private._id,
            auth=user_admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot link node \'{}\' to itself.'.format(node_private._id)

    def test_create_linked_registrations_relationship_registration_already_in_linked_registrations_returns_no_content(
            self, make_request, registration, node_private, user_admin_contrib):
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 204

    def test_can_create_linked_registration_relationship_to_private_registration_if_admin(
            self, make_request, user_admin_contrib, node_private):
        registration = RegistrationFactory(creator=user_admin_contrib)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 201
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id in linked_registrations

    def test_can_create_linked_registration_relationship_to_private_registration_if_rw(
            self, make_request, user_admin_contrib, node_private):
        registration = RegistrationFactory()
        registration.add_contributor(
            user_admin_contrib,
            auth=Auth(registration.creator))
        registration.save()
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 201
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id in linked_registrations

    def test_can_create_linked_registration_relationship_to_private_registration_if_read_only(
            self, make_request, user_admin_contrib, node_private):
        registration = RegistrationFactory()
        registration.add_contributor(
            user_admin_contrib,
            auth=Auth(registration.creator),
            permissions=READ)
        registration.save()
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 201
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id in linked_registrations


@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipUpdate(
        LinkedRegistrationsTestCase):

    @pytest.fixture()
    def make_payload(self):
        def payload(registration_id=None, deprecated_type=True):
            return {
                'data': [{
                    'type': 'linked_registrations' if deprecated_type else 'registrations',
                    'id': registration_id
                }]
            }
        return payload

    @pytest.fixture()
    def make_request(self, app, make_payload):
        def request(node_id=None, auth=None, reg_id=None, expect_errors=False, version=None, deprecated_type=True):
            url = '/{}nodes/{}/relationships/linked_registrations/'.format(
                API_BASE, node_id)
            if version:
                url = '{}?version={}'.format(url, version)
            if auth:
                return app.put_json_api(
                    url,
                    make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                    auth=auth, expect_errors=expect_errors)
            return app.put_json_api(
                url,
                make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                expect_errors=expect_errors)
        return request

    def test_admin_contributor_can_update_linked_registrations_relationship(
            self, make_request, registration, user_admin_contrib, node_private):
        registration_two = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration_two._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 200
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id not in linked_registrations
        assert registration_two._id in linked_registrations

    def test_admin_contributor_can_update_linked_registrations_relationship_2_13(
            self, make_request, registration, user_admin_contrib, node_private):
        registration_two = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration_two._id,
            auth=user_admin_contrib.auth,
            version='2.13',
            deprecated_type=False,
        )
        assert res.status_code == 200
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id not in linked_registrations
        assert registration_two._id in linked_registrations

    def test_rw_contributor_can_update_linked_registrations_relationship(
            self, make_request, registration, user_write_contrib, node_private):
        registration_two = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration_two._id,
            auth=user_write_contrib.auth
        )
        assert res.status_code == 200
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id not in linked_registrations
        assert registration_two._id in linked_registrations

    def test_empty_payload_removes_existing_linked_registrations(
            self, app, user_admin_contrib, registration, node_private):
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(
            API_BASE, node_private._id)
        res = app.put_json_api(url, {}, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id not in linked_registrations

    def test_cannot_update_linked_registrations_relationship(
            self, app, make_request, make_payload, user_read_contrib, user_non_contrib, node_private, user_admin_contrib):

        #   test_read_contributor_cannot_update_linked_registrations_relationship
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_non_contributor_cannot_update_linked_registrations_relationship
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_unauthenticated_user_cannot_update_linked_registrations_relationship
        registration = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_cannot_update_relationship_with_child_registration
        child_reg = RegistrationFactory(creator=user_admin_contrib)
        NodeRelationFactory(child=child_reg, parent=node_private)
        url = '/{}nodes/{}/relationships/linked_registrations/'.format(
            API_BASE, node_private._id)
        data = make_payload(registration_id=child_reg._id)
        res = app.put_json_api(url, data, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Target Node \'{}\' is already a child of \'{}\'.'.format(child_reg._id, node_private._id)

    #   test_cannot_update_link_registration_to_itself
        res = make_request(
            node_id=node_private._id,
            reg_id=node_private._id,
            auth=user_admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot link node \'{}\' to itself.'.format(node_private._id)

@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipDelete(
        LinkedRegistrationsTestCase):

    @pytest.fixture()
    def make_payload(self):
        def payload(registration_id=None, deprecated_type=True):
            return {
                'data': [{
                    'type': 'linked_registrations' if deprecated_type else 'registrations',
                    'id': registration_id
                }]
            }
        return payload

    @pytest.fixture()
    def make_request(self, app, make_payload):
        def request(node_id=None, auth=None, reg_id=None, expect_errors=False, version=None, deprecated_type=True):
            url = '/{}nodes/{}/relationships/linked_registrations/'.format(
                API_BASE, node_id)
            if version:
                url = '{}?version={}'.format(url, version)
            if auth:
                return app.delete_json_api(
                    url,
                    make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                    auth=auth, expect_errors=expect_errors)
            return app.delete_json_api(
                url,
                make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                expect_errors=expect_errors)
        return request

    def test_admin_contributor_can_delete_linked_registrations_relationship(
            self, make_request, registration, user_admin_contrib, node_private):
        res = make_request(
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id=registration._id
        )
        assert res.status_code == 204

    def test_admin_contributor_can_delete_linked_registrations_relationship_2_13(
            self, make_request, registration, user_admin_contrib, node_private):
        res = make_request(
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id=registration._id,
            version='2.13',
            deprecated_type=False,
        )
        assert res.status_code == 204

    def test_rw_contributor_can_delete_linked_registrations_relationship(
            self, make_request, registration, user_write_contrib, node_private):
        res = make_request(
            node_id=node_private._id,
            auth=user_write_contrib.auth,
            reg_id=registration._id
        )
        assert res.status_code == 204

    def test_linked_registrations_relationship_errors(
            self, make_request, registration, user_admin_contrib,
            user_read_contrib, user_non_contrib, node_private):

        #   test_read_contributor_cannot_delete_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            auth=user_read_contrib.auth,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_non_contributor_cannot_delete_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            auth=user_non_contrib.auth,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_unauthenticated_user_cannot_delete_linked_registrations_relationship
        res = make_request(
            node_id=node_private._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_cannot_delete_linked_registrations_relationship_invalid_registration_guid
        res = make_request(
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id='abcde',
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Pointer with id "abcde" not found in pointers list'

    #   test_cannot_delete_linked_registrations_relationship_registration_not_in_linked_registrations
        registration_two = RegistrationFactory(is_public=True)
        res = make_request(
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id=registration_two._id,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Pointer with id "{}" not found in pointers list'.format(
            registration_two._id)
