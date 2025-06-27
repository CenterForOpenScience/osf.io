import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.utils import LinkedRegistrationsTestCase
from osf_tests.factories import (
    RegistrationFactory,
    NodeRelationFactory,
)
from rest_framework import exceptions


@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipUpdate(LinkedRegistrationsTestCase):

    def make_payload(self, registration_id=None, deprecated_type=True):
        return {
            'data': [{
                'type': 'linked_registrations' if deprecated_type else 'registrations',
                'id': registration_id
            }]
        }

    def make_request(self, app, node_id=None, auth=None, reg_id=None, expect_errors=False, version=None, deprecated_type=True):
        url = f'/{API_BASE}nodes/{node_id}/relationships/linked_registrations/'
        if version:
            url = f'{url}?version={version}'
        if auth:
            return app.put_json_api(
                url,
                self.make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
                auth=auth, expect_errors=expect_errors
            )
        return app.put_json_api(
            url,
            self.make_payload(registration_id=reg_id, deprecated_type=deprecated_type),
            expect_errors=expect_errors
        )

    def test_admin_contributor_can_update_linked_registrations_relationship(
            self, app, registration, user_admin_contrib, node_private):
        registration_two = RegistrationFactory(is_public=True)
        res = self.make_request(
            app=app,
            node_id=node_private._id,
            reg_id=registration_two._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 200
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id not in linked_registrations
        assert registration_two._id in linked_registrations

    def test_admin_contributor_can_update_linked_registrations_relationship_2_13(
            self, app, registration, user_admin_contrib, node_private):
        registration_two = RegistrationFactory(is_public=True)
        res = self.make_request(
            app=app,
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
            self,
            app,
            registration,
            user_write_contrib,
            node_private
    ):
        registration_two = RegistrationFactory(is_public=True)
        res = self.make_request(
            app=app,
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
        url = f'/{API_BASE}nodes/{node_private._id}/relationships/linked_registrations/'
        res = app.put_json_api(url, {}, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        linked_registrations = [r['id'] for r in res.json['data']]
        assert registration._id not in linked_registrations

    def test_read_contributor_cannot_update_linked_registrations_relationship(
            self,
            app,
            user_read_contrib,
            user_non_contrib,
            node_private,
            user_admin_contrib
    ):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            app,
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_non_contributor_cannot_update_linked_registrations_relationship(
            self, app, user_read_contrib, user_non_contrib, node_private, user_admin_contrib):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            app=app,
            node_id=node_private._id,
            reg_id=registration._id,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_unauthenticated_user_cannot_update_linked_registrations_relationship(
            self, app, user_read_contrib, user_non_contrib, node_private, user_admin_contrib):
        registration = RegistrationFactory(is_public=True)
        res = self.make_request(
            app=app,
            node_id=node_private._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_cannot_update_relationship_with_child_registration(
            self, app, user_read_contrib, user_non_contrib, node_private, user_admin_contrib):
        child_reg = RegistrationFactory(creator=user_admin_contrib)
        NodeRelationFactory(child=child_reg, parent=node_private)
        data = self.make_payload(registration_id=child_reg._id)
        res = app.put_json_api(
            f'/{API_BASE}nodes/{node_private._id}/relationships/linked_registrations/',
            data,
            auth=user_admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f'Target Node \'{child_reg._id}\' is already a child of \'{node_private._id}\'.'

    def test_cannot_update_link_registration_to_itself(
            self, app, user_read_contrib, user_non_contrib, node_private, user_admin_contrib):
        res = self.make_request(
            app=app,
            node_id=node_private._id,
            reg_id=node_private._id,
            auth=user_admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f'Cannot link node \'{node_private._id}\' to itself.'
