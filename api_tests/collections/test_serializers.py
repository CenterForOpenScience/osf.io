# -*- coding: utf-8 -*-
from urlparse import urlparse

from nose.tools import *  # flake8: noqa

from tests.base import DbTestCase
from tests.utils import make_drf_request
from tests.factories import UserFactory, FolderFactory

from api.collections.serializers import CollectionSerializer


class TestNodeSerializer(DbTestCase):

    def setUp(self):
        super(TestNodeSerializer, self).setUp()
        self.user = UserFactory()

    def test_collection_serialization(self):
        collection = FolderFactory(creator=self.user)
        req = make_drf_request()
        result = CollectionSerializer(collection, context={'request': req}).data
        data = result['data']
        assert_equal(data['id'], collection._id)
        assert_equal(data['type'], 'collections')

        # Attributes
        attributes = data['attributes']
        assert_equal(attributes['title'], collection.title)
        assert_equal(attributes['date_created'], collection.date_created.isoformat())
        assert_equal(attributes['date_modified'], collection.date_modified.isoformat())

        # Relationships
        relationships = data['relationships']
        assert_in('node_links', relationships)
        # Bunch of stuff in Nodes that should not be in Collections
        assert_not_in('contributors', relationships)
        assert_not_in('files', relationships)
        assert_not_in('parent', relationships)
        assert_not_in('registrations', relationships)
        assert_not_in('forked_from', relationships)