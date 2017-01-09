# -*- coding: utf-8 -*-
from urlparse import urlparse

from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.utils import make_drf_request_with_version
from osf_tests.factories import UserFactory, CollectionFactory

from api.collections.serializers import CollectionSerializer


class TestNodeSerializer(ApiTestCase):

    def setUp(self):
        super(TestNodeSerializer, self).setUp()
        self.user = UserFactory()

    def test_collection_serialization(self):
        collection = CollectionFactory(creator=self.user)
        req = make_drf_request_with_version()
        if req.version >= '2.2':
            created_format = '%Y-%m-%dT%H:%M:%S.%fZ'
            modified_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        else:
            created_format = '%Y-%m-%dT%H:%M:%S.%f' if collection.date_created.microsecond else '%Y-%m-%dT%H:%M:%S'
            modified_format = '%Y-%m-%dT%H:%M:%S.%f' if collection.date_modified.microsecond else '%Y-%m-%dT%H:%M:%S'

        result = CollectionSerializer(collection, context={'request': req}).data
        data = result['data']
        assert_equal(data['id'], collection._id)
        assert_equal(data['type'], 'collections')
        # Attributes
        attributes = data['attributes']
        assert_equal(attributes['title'], collection.title)
        assert_equal(attributes['date_created'], collection.date_created.strftime(created_format))
        assert_equal(attributes['date_modified'], collection.date_modified.strftime(modified_format))
        assert_equal(attributes['bookmarks'], collection.is_bookmark_collection)

        # Relationships
        relationships = data['relationships']
        assert_in('node_links', relationships)
        # Bunch of stuff in Nodes that should not be in Collections
        assert_not_in('contributors', relationships)
        assert_not_in('files', relationships)
        assert_not_in('parent', relationships)
        assert_not_in('registrations', relationships)
        assert_not_in('forked_from', relationships)
