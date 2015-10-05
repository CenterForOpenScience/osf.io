# -*- coding: utf-8 -*-
from urlparse import urlparse

from nose.tools import *  # flake8: noqa
from django.http import HttpRequest
from dateutil.parser import parse as parse_date

from tests.base import DbTestCase, ApiTestCase, assert_datetime_equal
from tests.factories import UserFactory, RegistrationFactory

from api.nodes.serializers import NodeRegistrationSerializer
from api.base.settings.defaults import API_BASE

def make_test_request():
    from rest_framework.request import Request
    http_request = HttpRequest()
    http_request.META['SERVER_NAME'] = 'localhost'
    http_request.META['SERVER_PORT'] = 8000
    # A DRF Request wraps a Django HttpRequest
    return Request(http_request)

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
