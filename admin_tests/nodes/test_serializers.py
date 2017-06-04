from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase
from tests.factories import NodeFactory, UserFactory

from admin.nodes.serializers import serialize_simple_user, serialize_node


class TestNodeSerializers(AdminTestCase):
    def test_serialize_node(self):
        node = NodeFactory()
        info = serialize_node(node)
        assert_is_instance(info, dict)
        assert_equal(info['parent'], node.parent_id)
        assert_equal(info['title'], node.title)
        assert_equal(info['children'], [])
        assert_equal(info['id'], node._id)
        assert_equal(info['public'], node.is_public)
        assert_equal(len(info['contributors']), 1)
        assert_false(info['deleted'])

    def test_serialize_deleted(self):
        node = NodeFactory()
        info = serialize_node(node)
        assert_false(info['deleted'])
        node.is_deleted = True
        info = serialize_node(node)
        assert_true(info['deleted'])
        node.is_deleted = False
        info = serialize_node(node)
        assert_false(info['deleted'])

    def test_serialize_simple_user(self):
        user = UserFactory()
        info = serialize_simple_user((user._id, 'admin'))
        assert_is_instance(info, dict)
        assert_equal(info['id'], user._id)
        assert_equal(info['name'], user.fullname)
        assert_equal(info['permission'], 'admin')
