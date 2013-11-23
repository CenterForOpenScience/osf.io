import unittest
from nose.tools import *  # PEP8 asserts

from marshmallow import types

from website.project import serializers

from tests.factories import NodeLogFactory, NodeFactory
from tests.base import DbTestCase


class TestSerializers(DbTestCase):

    def test_log_serializer(self):
        node = NodeFactory(category="hypothesis")
        log = NodeLogFactory(params={'node': node._primary_key})
        node.logs.append(node)
        node.save()
        d = serializers.LogSerializer(log).data
        assert_equal(d['action'], log.action)
        assert_equal(d['category'], 'component')
        assert_equal(d['node']['url'], log.node.url)
        assert_equal(d['date'], types.rfcformat(log.date))
        assert_in('contributors', d)
        assert_equal(d['user']['fullname'], log.user.fullname)
        assert_equal(d['user']['url'], log.user.url)
        assert_in('api_key', d)
        assert_equal(d['params'], log.params)
        assert_equal(d['node']['title'], log.node.title)

if __name__ == '__main__':
    unittest.main()
