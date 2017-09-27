import pytest
from urlparse import urlparse

from api.collections.serializers import CollectionSerializer
from osf_tests.factories import (
    UserFactory,
    CollectionFactory,
)
from tests.utils import make_drf_request_with_version

@pytest.mark.django_db
class TestNodeSerializer:
    def test_collection_serialization(self):
        user = UserFactory()
        collection = CollectionFactory(creator=user)
        req = make_drf_request_with_version()
        if req.version >= '2.2':
            created_format = '%Y-%m-%dT%H:%M:%S.%fZ'
            modified_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        else:
            created_format = '%Y-%m-%dT%H:%M:%S.%f' if collection.date_created.microsecond else '%Y-%m-%dT%H:%M:%S'
            modified_format = '%Y-%m-%dT%H:%M:%S.%f' if collection.date_modified.microsecond else '%Y-%m-%dT%H:%M:%S'

        result = CollectionSerializer(collection, context={'request': req}).data
        data = result['data']
        assert data['id'] == collection._id
        assert data['type'] == 'collections'
        # Attributes
        attributes = data['attributes']
        assert attributes['title'] == collection.title
        assert attributes['date_created'] == collection.date_created.strftime(created_format)
        assert attributes['date_modified'] == collection.date_modified.strftime(modified_format)
        assert attributes['bookmarks'] == collection.is_bookmark_collection

        # Relationships
        relationships = data['relationships']
        assert 'node_links' in relationships
        # Bunch of stuff in Nodes that should not be in Collections
        assert 'contributors' not in relationships
        assert 'files' not in relationships
        assert 'parent' not in relationships
        assert 'registrations' not in relationships
        assert 'forked_from' not in relationships
