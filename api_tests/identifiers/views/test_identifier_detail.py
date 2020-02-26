import pytest
from future.moves.urllib.parse import urlparse
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    IdentifierFactory,
    NodeFactory,
    PreprintFactory
)
from osf.utils.permissions import READ
from osf.utils.workflows import DefaultStates


@pytest.mark.django_db
class TestIdentifierDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user, is_public=True)

    @pytest.fixture()
    def identifier_registration(self, registration):
        return IdentifierFactory(referent=registration)

    @pytest.fixture()
    def res_registration(self, app, identifier_registration):
        registration_url = '/{}identifiers/{}/'.format(
            API_BASE, identifier_registration._id)
        return app.get(registration_url)

    @pytest.fixture()
    def data_registration(self, res_registration):
        return res_registration.json['data']

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user, is_public=True)

    @pytest.fixture()
    def noncontrib(self, user):
        return AuthUserFactory()

    @pytest.fixture()
    def identifier_node(self, node):
        return IdentifierFactory(referent=node)

    @pytest.fixture()
    def res_node(self, app, identifier_node):
        url_node = '/{}identifiers/{}/'.format(API_BASE, identifier_node._id)
        return app.get(url_node)

    @pytest.fixture()
    def data_node(self, res_node):
        return res_node.json['data']

    @pytest.fixture()
    def preprint(self, user):
        preprint = PreprintFactory(creator=user)
        return preprint

    @pytest.fixture()
    def identifier_preprint(self, user, preprint):
        return IdentifierFactory(referent=preprint)

    def test_identifier_registration_detail(
            self, registration, identifier_registration,
            res_registration, data_registration
    ):

        # test_identifier_detail_success_registration
        assert res_registration.status_code == 200
        assert res_registration.content_type == 'application/vnd.api+json'

        # test_identifier_detail_returns_correct_referent_registration
        path = urlparse(
            data_registration['relationships']['referent']['links']['related']['href']
        ).path
        assert '/{}registrations/{}/'.format(
            API_BASE, registration._id) == path

        # test_identifier_detail_returns_correct_category_registration
        assert data_registration['attributes']['category'] == identifier_registration.category

        # test_identifier_detail_returns_correct_value_registration
        assert data_registration['attributes']['value'] == identifier_registration.value

    def test_identifier_node_detail(
            self, node, identifier_node,
            res_node, data_node
    ):

        # test_identifier_detail_success_node
        assert res_node.status_code == 200
        assert res_node.content_type == 'application/vnd.api+json'

        # test_identifier_detail_returns_correct_referent_node
        path = urlparse(
            data_node['relationships']['referent']['links']['related']['href']
        ).path
        assert '/{}nodes/{}/'.format(API_BASE, node._id) == path

        # test_identifier_detail_returns_correct_category_node
        assert data_node['attributes']['category'] == identifier_node.category

        # test_identifier_detail_returns_correct_value_node
        assert data_node['attributes']['value'] == identifier_node.value

    def test_identifier_preprint_detail(
            self, app, preprint, identifier_preprint,
            user
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, identifier_preprint._id)

        res = app.get(url, expect_errors=True)

        # test_identifier_detail_success_preprint
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        data = res.json['data']

        # test_identifier_detail_returns_correct_referent_preprint
        path = urlparse(
            data['relationships']['referent']['links']['related']['href']
        ).path
        assert '/{}preprints/{}/'.format(API_BASE, preprint._id) == path

        # test_identifier_detail_returns_correct_category_preprint
        assert data['attributes']['category'] == identifier_preprint.category

        # test_identifier_detail_returns_correct_value_preprint
        assert data['attributes']['value'] == identifier_preprint.value

    def test_identifier_preprint_detail_unpublished(
            self, app, preprint, user, identifier_preprint, noncontrib
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, identifier_preprint._id)
        preprint.is_published = False
        preprint.save()

        # test_unpublished_preprint_identifier_unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # test_unpublished_preprint_identifier_noncontrib_authenticated
        read_user = AuthUserFactory()
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_unpublished_preprint_identifier_readcontrib_authenticated
        read_user = AuthUserFactory()
        preprint.add_contributor(read_user, READ, save=True)
        res = app.get(url, auth=read_user.auth, expect_errors=True)
        assert res.status_code == 200

        # test_unpublished_preprint_identifier_admin_authenticated
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

    def test_identifier_preprint_detail_deleted(
            self, app, preprint, user, identifier_preprint, noncontrib
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, identifier_preprint._id)
        preprint.deleted = timezone.now()
        preprint.save()

        # test_deleted_preprint_identifier_unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

        # test_deleted_preprint_identifier_noncontrib_authenticated
        read_user = AuthUserFactory()
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 404

        # test_deleted_preprint_identifier_readcontrib_authenticated
        read_user = AuthUserFactory()
        preprint.add_contributor(read_user, READ, save=True)
        res = app.get(url, auth=read_user.auth, expect_errors=True)
        assert res.status_code == 404

        # test_deleted_preprint_identifier_admin_authenticated
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_identifier_preprint_detail_private(
            self, app, preprint, user, identifier_preprint, noncontrib
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, identifier_preprint._id)
        preprint.is_public = False
        preprint.save()

        # test_private_preprint_identifier_unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # test_private_preprint_identifier_noncontrib_authenticated
        read_user = AuthUserFactory()
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_private_preprint_identifier_readcontrib_authenticated
        read_user = AuthUserFactory()
        preprint.add_contributor(read_user, READ, save=True)
        res = app.get(url, auth=read_user.auth, expect_errors=True)
        assert res.status_code == 200

        # test_private_preprint_identifier_admin_authenticated
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_identifier_preprint_detail_abandoned(
            self, app, preprint, user, identifier_preprint, noncontrib
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, identifier_preprint._id)
        preprint.machine_state = DefaultStates.INITIAL.value
        preprint.save()

        # test_abandoned_preprint_identifier_unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # test_abandoned_preprint_identifier_noncontrib_authenticated
        read_user = AuthUserFactory()
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_abandoned_preprint_identifier_readcontrib_authenticated
        read_user = AuthUserFactory()
        preprint.add_contributor(read_user, READ, save=True)
        res = app.get(url, auth=read_user.auth, expect_errors=True)
        assert res.status_code == 403

        # test_abandoned_preprint_identifier_admin_authenticated
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_identifier_preprint_detail_orphaned(
            self, app, preprint, user, identifier_preprint, noncontrib
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, identifier_preprint._id)
        preprint.primary_file = None
        preprint.save()

        # test_orphaned_preprint_identifier_unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # test_orphaned_preprint_identifier_noncontrib_authenticated
        read_user = AuthUserFactory()
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_orphaned_preprint_identifier_readcontrib_authenticated
        read_user = AuthUserFactory()
        preprint.add_contributor(read_user, READ, save=True)
        res = app.get(url, auth=read_user.auth, expect_errors=True)
        assert res.status_code == 200

        # test_orphaned_preprint_identifier_admin_authenticated
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_invalid_identifier(
            self, app, user
    ):
        url = '/{}identifiers/{}/'.format(API_BASE, 'invalid_id')

        # test_unpublished_preprint_identifier_unauthenticated
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_identifier_preprint_detail_datacite_doi(self, app, user):
        """ Make sure dois with the temporary category legacy_doi show up
        with the category doi for now, until the proper migration happens
        """
        preprint = PreprintFactory(set_doi=False)
        doi_value = '10.123/datacitedoi/woo'
        preprint.set_identifier_value(category='legacy_doi', value=doi_value)
        identifier = preprint.identifiers.filter(category='legacy_doi').first()
        url = '/{}identifiers/{}/'.format(API_BASE, identifier._id)

        res = app.get(url, auth=user.auth)
        attributes = res.json['data']['attributes']

        assert attributes['category'] == 'doi'
        assert attributes['value'] == doi_value
