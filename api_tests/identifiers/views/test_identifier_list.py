import pytest
from urlparse import urlparse

from api.base.settings.defaults import API_BASE
from osf.models import Identifier
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    IdentifierFactory,
    NodeFactory,
    PreprintFactory,
)
from tests.utils import assert_items_equal

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def all_identifiers():
    return Identifier.objects.all()

@pytest.mark.django_db
class TestRegistrationIdentifierList:

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user, is_public=True)

    @pytest.fixture()
    def identifier_node(self, node):
        return IdentifierFactory(referent=node)

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user, is_public=True)

    @pytest.fixture()
    def identifier_registration(self, registration):
        return IdentifierFactory(referent=registration)

    @pytest.fixture()
    def url_registration_identifiers(self, registration):
        return '/{}registrations/{}/identifiers/'.format(API_BASE, registration._id)

    @pytest.fixture()
    def res_registration_identifiers(self, app, url_registration_identifiers):
        return app.get(url_registration_identifiers)

    @pytest.fixture()
    def data_registration_identifiers(self, res_registration_identifiers):
        return res_registration_identifiers.json['data']


    def test_identifier_list_success(self, res_registration_identifiers):
        assert res_registration_identifiers.status_code == 200
        assert res_registration_identifiers.content_type == 'application/vnd.api+json'

    def test_identifier_list_returns_correct_number_and_referent(self, registration, identifier_registration, data_registration_identifiers, res_registration_identifiers, all_identifiers):
        # test_identifier_list_returns_correct_number
        total = res_registration_identifiers.json['links']['meta']['total']
        assert total == all_identifiers.count()

        # test_identifier_list_returns_correct_referent
        paths = [
            urlparse(
                item['relationships']['referent']['links']['related']['href']
            ).path for item in data_registration_identifiers
        ]
        assert '/{}registrations/{}/'.format(API_BASE, registration._id) in paths

    def test_identifier_list_returns_correct_categories_and_values(self, all_identifiers, data_registration_identifiers):
        # test_identifier_list_returns_correct_categories
        categories = [identifier.category for identifier in all_identifiers]
        categories_in_response = [identifier['attributes']['category'] for identifier in data_registration_identifiers]
        assert_items_equal(categories_in_response, categories)

        # test_identifier_list_returns_correct_values
        values = [identifier.value for identifier in all_identifiers]
        values_in_response = [identifier['attributes']['value'] for identifier in data_registration_identifiers]
        assert_items_equal(values_in_response, values)

    def test_identifier_filter_by_category(self, app, registration, identifier_registration, url_registration_identifiers):
        IdentifierFactory(referent=registration, category='nopeid')
        identifiers_for_registration = registration.identifiers
        assert identifiers_for_registration.count() == 2
        assert_items_equal(
            list(identifiers_for_registration.values_list('category', flat=True)),
            ['carpid', 'nopeid']
        )

        filter_url = '{}?filter[category]=carpid'.format(url_registration_identifiers)
        new_res = app.get(filter_url)

        carpid_total = Identifier.objects.filter(category='carpid').count()

        total = new_res.json['links']['meta']['total']
        assert total == carpid_total

    def test_node_identifier_not_returned_from_registration_endpoint(self, node, identifier_node, identifier_registration, res_registration_identifiers, data_registration_identifiers):
        assert res_registration_identifiers.status_code == 200
        assert len(data_registration_identifiers) == 1
        assert identifier_registration._id == data_registration_identifiers[0]['id']
        assert identifier_node._id != data_registration_identifiers[0]['id']

    def test_node_not_allowed_from_registrations_endpoint(self, app, node, identifier_node):
        url = '/{}registrations/{}/identifiers/'.format(API_BASE, node._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

@pytest.mark.django_db
class TestNodeIdentifierList:

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user, is_public=True)

    @pytest.fixture()
    def identifier_node(self, node):
        return IdentifierFactory(referent=node)

    @pytest.fixture()
    def url_node_identifiers(self, node):
        return '/{}nodes/{}/identifiers/'.format(API_BASE, node._id)

    @pytest.fixture()
    def res_node_identifiers(self, app, url_node_identifiers):
        return app.get(url_node_identifiers)

    @pytest.fixture()
    def data_node_identifiers(self, res_node_identifiers):
        return res_node_identifiers.json['data']

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user, is_public=True)

    @pytest.fixture()
    def identifier_registration(self, registration):
        return IdentifierFactory(referent=registration)

    def test_identifier_list_success(self, res_node_identifiers):
        assert res_node_identifiers.status_code == 200
        assert res_node_identifiers.content_type == 'application/vnd.api+json'

    def test_identifier_list_returns_correct_number_and_referent(self, node, identifier_node, res_node_identifiers, data_node_identifiers, all_identifiers):
        # test_identifier_list_returns_correct_number
        total = res_node_identifiers.json['links']['meta']['total']
        assert total == all_identifiers.count()

        #test_identifier_list_returns_correct_referent
        paths = [
            urlparse(
                item['relationships']['referent']['links']['related']['href']
            ).path for item in data_node_identifiers
        ]
        assert '/{}nodes/{}/'.format(API_BASE, node._id) in paths

    def test_identifier_list_returns_correct_categories_and_values(self, all_identifiers, data_node_identifiers):
        # test_identifier_list_returns_correct_categories
        categories = [identifier.category for identifier in all_identifiers]
        categories_in_response = [identifier['attributes']['category'] for identifier in data_node_identifiers]
        assert_items_equal(categories_in_response, categories)

        # test_identifier_list_returns_correct_values
        values = [identifier.value for identifier in all_identifiers]
        values_in_response = [identifier['attributes']['value'] for identifier in data_node_identifiers]
        assert_items_equal(values_in_response, values)

    def test_identifier_filter_by_category(self, app, node, identifier_node, url_node_identifiers):
        IdentifierFactory(referent=node, category='nopeid')
        identifiers_for_node = Identifier.objects.filter(object_id=node.id)

        assert identifiers_for_node.count() == 2
        assert_items_equal(
            [identifier.category for identifier in identifiers_for_node],
            ['carpid', 'nopeid']
        )

        filter_url = '{}?filter[category]=carpid'.format(url_node_identifiers)
        new_res = app.get(filter_url)

        carpid_total = Identifier.objects.filter(category='carpid').count()

        total = new_res.json['links']['meta']['total']
        assert total == carpid_total

    def test_registration_identifier_not_returned_from_registration_endpoint(self, registration, identifier_node, identifier_registration, res_node_identifiers, data_node_identifiers):
        assert res_node_identifiers.status_code == 200
        assert len(data_node_identifiers) == 1
        assert identifier_node._id == data_node_identifiers[0]['id']
        assert identifier_registration._id != data_node_identifiers[0]['id']

    def test_registration_not_allowed_from_nodes_endpoint(self, app, registration, identifier_registration):
        url = '/{}nodes/{}/identifiers/'.format(API_BASE, registration._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestPreprintIdentifierList:

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def url_preprint_identifier(self, preprint):
        return '/{}preprints/{}/identifiers/'.format(API_BASE, preprint._id)

    @pytest.fixture()
    def res_preprint_identifier(self, app, url_preprint_identifier):
        return app.get(url_preprint_identifier)

    @pytest.fixture()
    def data_preprint_identifier(self, res_preprint_identifier):
        return res_preprint_identifier.json['data']

    def test_identifier_list_success(self, res_preprint_identifier):
        assert res_preprint_identifier.status_code == 200
        assert res_preprint_identifier.content_type == 'application/vnd.api+json'

    def test_identifier_list_returns_correct_number_and_referent(self, preprint, res_preprint_identifier, data_preprint_identifier, all_identifiers, user):
        # add another preprint so there are more identifiers
        PreprintFactory(creator=user)

        # test_identifier_list_returns_correct_number
        total = res_preprint_identifier.json['links']['meta']['total']
        assert total == Identifier.objects.filter(object_id=preprint.id).count()

        # test_identifier_list_returns_correct_referent
        paths = [
            urlparse(
                item['relationships']['referent']['links']['related']['href']
            ).path for item in data_preprint_identifier
        ]
        assert '/{}preprints/{}/'.format(API_BASE, preprint._id) in paths

    def test_identifier_list_returns_correct_categories_and_values(self, all_identifiers, data_preprint_identifier):
        # test_identifier_list_returns_correct_categories
        categories = all_identifiers.values_list('category', flat=True)
        categories_in_response = [identifier['attributes']['category'] for identifier in data_preprint_identifier]
        assert_items_equal(categories_in_response, list(categories))

        # test_identifier_list_returns_correct_values
        values = all_identifiers.values_list('value', flat=True)
        values_in_response = [identifier['attributes']['value'] for identifier in data_preprint_identifier]
        assert_items_equal(values_in_response, list(values))
