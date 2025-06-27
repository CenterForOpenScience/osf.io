import pytest

from api.base.settings.defaults import API_BASE
from osf.models import Outcome, Identifier, OutcomeArtifact
from osf.utils.outcomes import ArtifactTypes
from osf_tests.factories import (
    AuthUserFactory,
    OSFGroupFactory,
)
from osf.utils.permissions import READ
from rest_framework import exceptions
from .utils import LinkedRegistrationsTestCase


@pytest.mark.django_db
class TestNodeLinkedRegistrationsList(LinkedRegistrationsTestCase):

    def make_request(self, app, node_id=None, auth=None, expect_errors=False):
        url = f'/{API_BASE}nodes/{node_id}/linked_registrations/'
        if auth:
            return app.get(url, auth=auth, expect_errors=expect_errors)
        return app.get(url, expect_errors=expect_errors)

    def test_public_node_unauthenticated_user_can_view_linked_registrations(self, app, node_public, registration):
        res = self.make_request(app, node_id=node_public._id)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_node_registrations_links_registrations_artifacts(self, app, registration, user_admin_contrib, node_private):
        outcome = Outcome.objects.create()
        registration_doi = Identifier.objects.create(
            referent=registration,
            value='SOME_PROJECT_DOI',
            category='doi'
        )
        # Create the PRIMARY artifact for this registration, so the annotations can resolve
        OutcomeArtifact.objects.create(
            outcome=outcome,
            identifier=registration_doi,
            artifact_type=ArtifactTypes.PRIMARY,
            finalized=True,
        )
        # Now create the DATA artifact for the same outcome
        OutcomeArtifact.objects.create(
            outcome=outcome,
            identifier=registration_doi,
            artifact_type=ArtifactTypes.PAPERS,
            finalized=True,
        )

        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth
        )
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['has_papers']  # here and true!
        assert res.json['data'][0]['attributes']['has_data'] is False  # here and false!
        assert res.json['data'][0]['attributes']['has_analytic_code'] is False
        assert res.json['data'][0]['attributes']['has_materials'] is False
        assert res.json['data'][0]['attributes']['has_supplements'] is False

    def test_private_node_admin_contributor_can_view_linked_registrations(
            self,
            app,
            node_private,
            user_admin_contrib,
            registration
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_private_node_rw_contributor_can_view_linked_registrations(
            self,
            app,
            user_write_contrib,
            registration,
            node_private
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_write_contrib.auth
        )
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_private_node_read_contributor_can_view_linked_registrations(
            self,
            app,
            user_read_contrib,
            registration,
            node_private
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_read_contrib.auth
        )
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_private_node_non_contributor_cannot_view_linked_registrations(
            self,
            app,
            user_non_contrib,
            registration,
            node_private
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_private_node_unauthenticated_user_cannot_view_linked_registrations(self, app, node_private):
        res = self.make_request(
            app,
            node_id=node_private._id,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_osf_group_member_read_can_view_linked_reg(
            self,
            app,
            user_admin_contrib,
            user_write_contrib,
            user_read_contrib,
            user_non_contrib,
            registration,
            node_public,
            node_private
    ):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_private.add_osf_group(group, READ)
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=group_mem.auth,
            expect_errors=True
        )
        assert res.status_code == 200


@pytest.mark.django_db
class TestNodeLinkedRegistrationsRelationshipRetrieve(LinkedRegistrationsTestCase):

    def make_request(self, app, node_id=None, auth=None, expect_errors=False, version=None):
        url = f'/{API_BASE}nodes/{node_id}/relationships/linked_registrations/'
        if version:
            url = f'{url}?version={version}'
        if auth:
            return app.get(url, auth=auth, expect_errors=expect_errors)
        return app.get(url, expect_errors=expect_errors)

    def test_public_node_unauthenticated_user_can_view_linked_registrations_relationship(
        self,
        app,
        registration,
        node_public
    ):
        res = self.make_request(app, node_id=node_public._id)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id
        assert res.json['data'][0]['type'] == 'linked_registrations'

    def test_public_node_unauthenticated_user_can_view_linked_registrations_relationship_2_13(
        self,
        app,
        registration,
        node_public
    ):

        res = self.make_request(app, node_id=node_public._id, version='2.13')
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id
        assert res.json['data'][0]['type'] == 'registrations'

    def test_private_node_admin_contributor_can_view_linked_registrations_relationship(
        self,
        app,
        registration,
        node_private,
        node_public,
        user_admin_contrib
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_admin_contrib.auth
        )
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_private_node_rw_contributor_can_view_linked_registrations_relationship(
            self,
            app,
            registration,
            node_private,
            node_public,
            user_write_contrib
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_write_contrib.auth
        )
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_private_node_read_contributor_can_view_linked_registrations_relationship(
            self,
            app,
            registration,
            node_private,
            node_public,
            user_read_contrib
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_read_contrib.auth
        )
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == registration._id

    def test_private_node_non_contributor_cannot_view_linked_registrations_relationship(
            self,
            app,
            registration,
            node_private,
            node_public,
            user_non_contrib
    ):
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_private_node_unauthenticated_user_cannot_view_linked_registrations_relationship(
            self,
            app,
            registration,
            node_private,
            node_public,
            user_non_contrib
    ):
        res = self.make_request(app, node_id=node_private._id, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_osf_group_member_can_view_linked_registration_relationship(
            self,
            app,
            registration,
            node_private,
            node_public,
            user_non_contrib
    ):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_private.add_osf_group(group, READ)
        res = self.make_request(
            app,
            node_id=node_private._id,
            auth=group_mem.auth,
            expect_errors=True
        )
        assert res.status_code == 200
