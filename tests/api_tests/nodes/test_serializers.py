# -*- coding: utf-8 -*-
from urlparse import urlparse

from nose.tools import *  # flake8: noqa
from django.http import HttpRequest
from dateutil.parser import parse as parse_date

from tests.base import DbTestCase, ApiTestCase, assert_datetime_equal
from tests.factories import UserFactory, NodeFactory, RegistrationFactory

from api.nodes.serializers import NodeSerializer, NodeRegistrationSerializer
from api.base.settings.defaults import API_BASE

def make_test_request():
    from rest_framework.request import Request
    http_request = HttpRequest()
    http_request.META['SERVER_NAME'] = 'localhost'
    http_request.META['SERVER_PORT'] = 8000
    # A DRF Request wraps a Django HttpRequest
    return Request(http_request)


class TestNodeSerializer(DbTestCase):

    def test_serialization(self):
        user = UserFactory()
        node = NodeFactory()
        req = make_test_request()
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
        assert_equal(attributes['collection'], node.is_fork)

        # Relationships
        relationships = data['relationships']
        assert_in('children', relationships)
        assert_in('contributors', relationships)
        assert_in('files', relationships)
        assert_in('parent', relationships)
        assert_in('registrations', relationships)


class TestNodeRegistrationSerializer(DbTestCase):

    def test_serialization(self):
        user = UserFactory()
        req = make_test_request()
        reg = RegistrationFactory(creator=user)
        result = NodeRegistrationSerializer(reg, context={'request': req}).data
        data = result['data']
        assert_equal(data['id'], reg._id)
        assert_equal(data['type'], 'nodes')

        # Attributes
        attributes = data['attributes']
        assert_datetime_equal(
            parse_date(attributes['date_registered']),
            reg.registered_date
        )
        assert_equal(attributes['retracted'], reg.is_retracted)

        # Relationships
        relationships = data['relationships']
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
