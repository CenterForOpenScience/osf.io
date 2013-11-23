import unittest
from nose.tools import *  # PEP8 asserts

from marshmallow import utils

from website.project import serializers

from tests.factories import NodeLogFactory, NodeFactory, ProjectFactory, UserFactory
from tests.base import DbTestCase


class TestSerializers(DbTestCase):

    def test_log_serializer(self):
        node = NodeFactory(category="hypothesis")
        log = NodeLogFactory(params={'node': node._primary_key})
        node.logs.append(log)
        node.save()
        serialized = serializers.LogSerializer(log)
        assert_true(serialized.is_valid())
        d = serialized.data
        assert_equal(d['action'], log.action)
        assert_equal(d['node']['category'], 'component')
        assert_equal(d['node']['url'], log.node.url)
        assert_equal(d['date'], utils.rfcformat(log.date))
        assert_in('contributors', d)
        assert_equal(d['user']['fullname'], log.user.fullname)
        assert_equal(d['user']['url'], log.user.url)
        assert_in('api_key', d)
        assert_equal(d['params'], log.params)
        assert_equal(d['node']['title'], log.node.title)

    def test_node_serializer(self):
        node = ProjectFactory()
        log = NodeLogFactory(params={'node': node._primary_key})
        node.logs.append(log)
        node.save()
        date_modified = node.logs[-1].date
        serialized = serializers.NodeSerializer(node)
        assert_true(serialized.is_valid())
        d = serialized.data
        assert_equal(d['id'], node._id)
        assert_equal(d['title'], node.title)
        assert_equal(d['category'], node.project_or_component)
        assert_equal(d['description'], node.description)
        assert_equal(d['url'], node.url)
        assert_equal(d['api_url'], node.api_url)
        assert_equal(d['is_public'], node.is_public)
        assert_equal(d['tags'], [t._primary_key for t in node.tags])
        assert_equal(d['children'], bool(node.nodes))
        assert_equal(d['is_registration'], node.is_registration)
        assert_in('registered_from_url', d)
        assert_equal(d['registration_count'], 0)
        assert_equal(d['is_fork'], node.is_fork)
        assert_in('forked_from_url', d)
        assert_equal(d['fork_count'], 0)
        assert_in('forked_date', d)
        assert_in('watched_count', d)
        assert_equal(d['logs'], serializers.LogSerializer(node.get_recent_logs()).data)
        assert_equal(d['date_created'], utils.rfcformat(node.date_created))
        assert_equal(d['date_modified'], utils.rfcformat(date_modified))

    def test_user_serializer(self):
        user = UserFactory()
        d = serializers.UserSerializer(user).data
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['gravatar'], user.gravatar_url)

if __name__ == '__main__':
    unittest.main()
