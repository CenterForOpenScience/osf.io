from dateutil.parser import parse as parse_date
import pytest
from future.moves.urllib.parse import urlparse

from api.base.settings.defaults import API_BASE
from api.nodes.serializers import NodeSerializer
from api.sparse.serializers import SparseNodeSerializer, SparseRegistrationSerializer
from api.registrations.serializers import RegistrationSerializer
from framework.auth import Auth
from osf_tests.factories import (
    AuthUserFactory,
    UserFactory,
    NodeFactory,
    RegistrationFactory,
    ProjectFactory
)
from tests.base import assert_datetime_equal
from tests.utils import make_drf_request_with_version


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeSerializer:

    def test_node_serializer(self, user):

        #   test_node_serialization
        parent = ProjectFactory(creator=user)
        node = NodeFactory(creator=user, parent=parent)
        req = make_drf_request_with_version(version='2.0')
        result = NodeSerializer(node, context={'request': req}).data
        data = result['data']
        assert data['id'] == node._id
        assert data['type'] == 'nodes'

        # Attributes
        attributes = data['attributes']
        assert attributes['title'] == node.title
        assert attributes['description'] == node.description
        assert attributes['public'] == node.is_public
        assert set(attributes['tags']) == set(node.tags.values_list('name', flat=True))
        assert not attributes['current_user_can_comment']
        assert attributes['category'] == node.category
        assert attributes['registration'] == node.is_registration
        assert attributes['fork'] == node.is_fork
        assert attributes['collection'] == node.is_collection
        assert attributes['analytics_key'] == node.keenio_read_key
        assert attributes['wiki_enabled'] == node.has_addon('wiki')

        # Relationships
        relationships = data['relationships']
        assert 'region' in relationships
        assert 'children' in relationships
        assert 'contributors' in relationships
        assert 'files' in relationships
        assert 'parent' in relationships
        assert 'affiliated_institutions' in relationships
        assert 'registrations' in relationships
        assert 'forked_from' not in relationships
        parent_link = relationships['parent']['links']['related']['href']
        assert urlparse(
            parent_link).path == '/{}nodes/{}/'.format(API_BASE, parent._id)

    #   test_fork_serialization
        node = NodeFactory(creator=user)
        fork = node.fork_node(auth=Auth(user))
        req = make_drf_request_with_version(version='2.0')
        result = NodeSerializer(fork, context={'request': req}).data
        data = result['data']

        # Relationships
        relationships = data['relationships']
        forked_from = relationships['forked_from']['links']['related']['href']
        assert urlparse(
            forked_from).path == '/{}nodes/{}/'.format(API_BASE, node._id)

    #   test_template_serialization
        node = NodeFactory(creator=user)
        fork = node.use_as_template(auth=Auth(user))
        req = make_drf_request_with_version(version='2.0')
        result = NodeSerializer(fork, context={'request': req}).data
        data = result['data']

        # Relationships
        relationships = data['relationships']
        templated_from = relationships['template_node']['links']['related']['href']
        assert urlparse(
            templated_from).path == '/{}nodes/{}/'.format(API_BASE, node._id)


@pytest.mark.django_db
class TestSparseNodeSerializer:

    def test_sparse_node_serializer(self, user):

        #   test_node_serialization
        parent = ProjectFactory(creator=user)
        node = NodeFactory(creator=user, parent=parent)
        req = make_drf_request_with_version(version='2.15')
        result = SparseNodeSerializer(node, context={'request': req}).data
        data = result['data']
        assert data['id'] == node._id
        assert data['type'] == 'sparse-nodes'

        # Attributes
        attributes = data['attributes']
        assert attributes['title'] == node.title
        assert attributes['description'] == node.description
        assert attributes['public'] == node.is_public
        assert set(attributes['tags']) == set(node.tags.values_list('name', flat=True))
        assert 'current_user_can_comment' not in attributes
        assert 'license' not in attributes
        assert attributes['category'] == node.category
        assert 'registration' not in attributes
        assert attributes['fork'] == node.is_fork

        # Relationships
        relationships = data['relationships']
        assert 'region' not in relationships
        assert 'children' in relationships
        assert 'detail' in relationships
        assert 'contributors' in relationships
        assert 'files' not in relationships
        assert 'parent' in relationships
        assert 'affiliated_institutions' not in relationships
        assert 'registrations' not in relationships
        assert 'forked_from' not in relationships
        parent_link = relationships['parent']['links']['related']['href']
        assert urlparse(parent_link).path == '/{}sparse/nodes/{}/'.format(API_BASE, parent._id)
        assert 'sparse' not in relationships['detail']['links']['related']['href']
        sparse_children_path = urlparse(relationships['children']['links']['related']['href']).path
        assert sparse_children_path == '/{}sparse/nodes/{}/children/'.format(API_BASE, node._id)


@pytest.mark.django_db
class TestNodeRegistrationSerializer:

    def test_serialization(self):
        user = UserFactory()
        versioned_request = make_drf_request_with_version(version='2.2')
        registration = RegistrationFactory(creator=user)
        result = RegistrationSerializer(
            registration, context={
                'request': versioned_request}).data
        data = result['data']
        assert data['id'] == registration._id
        assert data['type'] == 'registrations'
        should_not_relate_to_registrations = [
            'registered_from',
            'registered_by',
            'registration_schema',
            'region',
            'provider',
            'storage',
            'groups',
        ]

        # Attributes
        attributes = data['attributes']
        assert_datetime_equal(
            parse_date(attributes['date_registered']),
            registration.registered_date
        )
        assert attributes['withdrawn'] == registration.is_retracted

        # Relationships
        relationships = data['relationships']

        # Relationships with data
        relationship_urls = {
            k: v['links']['related']['href'] for k, v
            in relationships.items()}

        assert 'registered_by' in relationships
        registered_by = relationships['registered_by']['links']['related']['href']
        assert urlparse(
            registered_by).path == '/{}users/{}/'.format(API_BASE, user._id)
        assert 'registered_from' in relationships
        registered_from = relationships['registered_from']['links']['related']['href']
        assert urlparse(registered_from).path == '/{}nodes/{}/'.format(
            API_BASE, registration.registered_from._id)
        api_registrations_url = '/{}registrations/'.format(API_BASE)
        for relationship in relationship_urls:
            if relationship in should_not_relate_to_registrations:
                assert api_registrations_url not in relationship_urls[relationship]
            else:
                assert api_registrations_url in relationship_urls[relationship], 'For key {}'.format(
                    relationship)


@pytest.mark.django_db
class TestSparseRegistrationSerializer:

    def test_sparse_registration_serializer(self, user):
        user = UserFactory()
        versioned_request = make_drf_request_with_version(version='2.2')
        registration = RegistrationFactory(creator=user)
        result = SparseRegistrationSerializer(
            registration, context={
                'request': versioned_request}).data
        data = result['data']
        assert data['id'] == registration._id
        assert data['type'] == 'sparse-registrations'

        # Attributes
        attributes = data['attributes']
        assert attributes['withdrawn'] == registration.is_retracted
        assert attributes['title'] == registration.title
        assert attributes['description'] == registration.description
        assert attributes['public'] == registration.is_public
        assert set(attributes['tags']) == set(registration.tags.values_list('name', flat=True))
        assert 'current_user_can_comment' not in attributes
        assert 'license' not in attributes
        assert attributes['category'] == registration.category
        assert attributes['fork'] == registration.is_fork

        # Relationships
        relationships = data['relationships']
        assert 'registered_by' not in relationships
        assert 'registered_from' not in relationships
        assert 'region' not in relationships
        assert 'children' in relationships
        assert 'detail' in relationships
        assert 'contributors' in relationships
        assert 'files' not in relationships
        assert 'affiliated_institutions' not in relationships
        assert 'registrations' not in relationships
        assert 'forked_from' not in relationships
        assert 'sparse' not in relationships['detail']['links']['related']['href']
        assert 'sparse' in relationships['children']['links']['related']['href']
