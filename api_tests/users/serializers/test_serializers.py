import pytest
import mock

from api.users.serializers import UserSerializer
from osf_tests.factories import (
    UserFactory,
    PreprintFactory
)
from tests.utils import make_drf_request_with_version


@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def user_with_preprint():
    preprint = PreprintFactory(is_published=True)
    preprint.save()
    preprint.node.creator.save()
    return preprint.node.creator


@pytest.mark.django_db
class TestUserSerializer:

    def test_user_serializer(self, user):
        req = make_drf_request_with_version(version='2.0')
        result = UserSerializer(user, context={'request': req}).data
        data = result['data']
        assert data['id'] == user._id
        assert data['type'] == 'users'

        # Attributes
        attributes = data['attributes']
        assert attributes['family_name'] == user.family_name
        assert attributes['given_name'] == user.given_name
        assert attributes['active'] == user.is_active
        assert attributes['employment'] == user.jobs
        assert attributes['education'] == user.schools

        # Relationships
        relationships = data['relationships']
        assert 'quickfiles' in relationships
        assert 'nodes' in relationships
        assert 'institutions' in relationships
        assert 'preprints' in relationships
        assert 'registrations' in relationships

    def test_user_serializer_with_related_counts(self, user):
        req = make_drf_request_with_version(version='2.0')
        req.query_params['related_counts'] = True
        result = UserSerializer(user, context={'request': req}).data
        data = result['data']

        # Relationships
        relationships = data['relationships']
        assert relationships['quickfiles']['links']['related']['meta']['count'] == 0
        assert relationships['nodes']['links']['related']['meta']['count'] == 0
        assert relationships['institutions']['links']['related']['meta']['count'] == 0
        assert relationships['preprints']['links']['related']['meta']['count'] == 0
        assert relationships['registrations']['links']['related']['meta']['count'] == 0

    def test_user_serializer_get_preprint_count(self, user_with_preprint):

        req = make_drf_request_with_version(version='2.0')
        req.query_params['related_counts'] = True
        result = UserSerializer(user_with_preprint, context={'request': req}).data
        data = result['data']

        assert data['relationships']['preprints']['links']['related']['meta']['count'] == 1
