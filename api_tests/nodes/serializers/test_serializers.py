# -*- coding: utf-8 -*-
from urlparse import urlparse

from nose.tools import *  # flake8: noqa
from dateutil.parser import parse as parse_date

from tests.base import DbTestCase, assert_datetime_equal
from tests.utils import make_drf_request
from tests.factories import UserFactory, NodeFactory, RegistrationFactory, ProjectFactory

from framework.auth import Auth
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.base.settings.defaults import API_BASE


class TestNodeSerializer(DbTestCase):

    def setUp(self):
        super(TestNodeSerializer, self).setUp()
        self.user = UserFactory()

    def test_node_serialization(self):
        parent = ProjectFactory(creator=self.user)
        node = NodeFactory(creator=self.user, parent=parent)
        req = make_drf_request()
        result = NodeSerializer(node, context={'request': req}).data
        data = result['data']
        assert_equal(data['id'], node._id)
        assert_equal(data['type'], 'nodes')

        # Attributes
        attributes = data['attributes']
        assert_equal(attributes['title'], node.title)
        assert_equal(attributes['description'], node.description)
        assert_equal(attributes['public'], node.is_public)
        assert_equal(attributes['tags'], [str(each) for each in node.tags])
        assert_equal(attributes['category'], node.category)
        assert_equal(attributes['registration'], node.is_registration)
        assert_equal(attributes['fork'], node.is_fork)
        assert_equal(attributes['collection'], node.is_collection)

        # Relationships
        relationships = data['relationships']
        assert_in('children', relationships)
        assert_in('contributors', relationships)
        assert_in('files', relationships)
        assert_in('parent', relationships)
        assert_in('primary_institution', relationships)
        parent_link = relationships['parent']['links']['related']['href']
        assert_equal(
            urlparse(parent_link).path,
            '/{}nodes/{}/'.format(API_BASE, parent._id)
        )
        assert_in('registrations', relationships)
        # Not a fork, so forked_from is removed entirely
        assert_not_in('forked_from', relationships)

    def test_fork_serialization(self):
        node = NodeFactory(creator=self.user)
        fork = node.fork_node(auth=Auth(user=node.creator))
        result = NodeSerializer(fork, context={'request': make_drf_request()}).data
        data = result['data']

        # Relationships
        relationships = data['relationships']
        forked_from = relationships['forked_from']['links']['related']['href']
        assert_equal(
            urlparse(forked_from).path,
            '/{}nodes/{}/'.format(API_BASE, node._id)
        )

class TestNodeRegistrationSerializer(DbTestCase):

    def test_serialization(self):
        user = UserFactory()
        req = make_drf_request()
        reg = RegistrationFactory(creator=user)
        result = RegistrationSerializer(reg, context={'request': req}).data
        data = result['data']
        assert_equal(data['id'], reg._id)
        assert_equal(data['type'], 'registrations')
        should_not_relate_to_registrations = [
            'registered_from',
            'registered_by',
        ]

        # Attributes
        attributes = data['attributes']
        assert_datetime_equal(
            parse_date(attributes['date_registered']),
            reg.registered_date
        )
        assert_equal(attributes['withdrawn'], reg.is_retracted)

        # Relationships
        relationships = data['relationships']
        relationship_urls = {}
        for relationship in relationships:
            relationship_urls[relationship]=relationships[relationship]['links']['related']['href']
        assert_in('registered_by', relationships)
        registered_by = relationships['registered_by']['links']['related']['href']
        assert_equal(
            urlparse(registered_by).path,
            '/{}users/{}/'.format(API_BASE, user._id)
        )
        assert_in('registered_from', relationships)
        registered_from = relationships['registered_from']['links']['related']['href']
        assert_equal(
            urlparse(registered_from).path,
            '/{}nodes/{}/'.format(API_BASE, reg.registered_from._id)
        )
        for relationship in relationship_urls:
            if relationship in should_not_relate_to_registrations:
                assert_not_in('/{}registrations/'.format(API_BASE), relationship_urls[relationship])
            else:
                assert_in('/{}registrations/'.format(API_BASE), relationship_urls[relationship],
                          'For key {}'.format(relationship))
