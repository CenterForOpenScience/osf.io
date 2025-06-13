import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import RegistrationFactory
from rest_framework import exceptions
from .utils import LinkedRegistrationsTestCase


@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipDelete(LinkedRegistrationsTestCase):

    def make_payload(self, registration_id=None, deprecated_type=True):
        return {
            'data': [
                {
                    'type': 'linked_registrations' if deprecated_type else 'registrations',
                    'id': registration_id
                }
            ]
        }

    def make_request(self, app, node_id=None, auth=None, reg_id=None, expect_errors=False, version=None, deprecated_type=True):
        url = f'/{API_BASE}nodes/{node_id}/relationships/linked_registrations/'
        if version:
            url = f'{url}?version={version}'
        if auth:
            return app.delete_json_api(
                url,
                self.make_payload(
                    registration_id=reg_id,
                    deprecated_type=deprecated_type
                ),
                auth=auth,
                expect_errors=expect_errors
            )
        return app.delete_json_api(
            url,
            self.make_payload(
                registration_id=reg_id,
                deprecated_type=deprecated_type
            ),
            expect_errors=expect_errors
        )

    def test_admin_contributor_can_delete_linked_registrations_relationship(
            self, app, registration, user_admin_contrib, node_private
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id=registration._id
        )
        assert res.status_code == 204

    def test_admin_contributor_can_delete_linked_registrations_relationship_2_13(
            self, app, registration, user_admin_contrib, node_private):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id=registration._id,
            version='2.13',
            deprecated_type=False,
        )
        assert res.status_code == 204

    def test_rw_contributor_can_delete_linked_registrations_relationship(
            self, app, registration, user_write_contrib, node_private):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_write_contrib.auth,
            reg_id=registration._id
        )
        assert res.status_code == 204

    def test_read_contributor_cannot_delete_linked_registrations_relationship(
            self, app, registration, user_admin_contrib, user_read_contrib, node_private
    ):

        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_read_contrib.auth,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_non_contributor_cannot_delete_linked_registrations_relationship(
        self, app, registration, user_admin_contrib, user_read_contrib, user_non_contrib, node_private
    ):

        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_non_contrib.auth,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_unauthenticated_user_cannot_delete_linked_registrations_relationship(
            self, app, registration, user_admin_contrib, user_read_contrib, user_non_contrib, node_private
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            reg_id=registration._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_cannot_delete_linked_registrations_relationship_invalid_registration_guid(
            self, app, registration, user_admin_contrib, user_read_contrib, user_non_contrib, node_private
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id='abcde',
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Pointer with id "abcde" not found in pointers list'

    def test_cannot_delete_linked_registrations_relationship_registration_not_in_linked_registrations(
        self, app, registration, user_admin_contrib, user_read_contrib, user_non_contrib, node_private
    ):

        registration_two = RegistrationFactory(is_public=True)
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth,
            reg_id=registration_two._id,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == f'Pointer with id "{registration_two._id}" not found in pointers list'
