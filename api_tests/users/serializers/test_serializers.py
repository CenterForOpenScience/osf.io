import pytest
import mock

from api.users.serializers import UserSerializer
from osf_tests.factories import (
    UserFactory,
)
from tests.utils import make_drf_request_with_version


@pytest.fixture()
@mock.patch('website.search.elastic_search.update_user')
def user(mock_update_user):
    user = UserFactory()
    user.jobs = [{
        'title': 'Veterinarian/Owner',
        'ongoing': True,
        'startYear': '2009',
        'startMonth': 4,
        'institution': 'Happy Paws Vet'
    }]
    user.schools = [{
        'endYear': '1994',
        'ongoing': False,
        'endMonth': 6,
        'startYear': '1990',
        'department': 'Veterinary Medicine',
        'startMonth': 8,
        'institution': 'UC Davis'
    }]
    user.save()
    return user


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
