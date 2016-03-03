from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase
from tests.factories import NodeFactory, UserFactory

from admin.users.serializers import serialize_user, serialize_simple_node


class TestUserSerializers(AdminTestCase):

    def test_serialize_user(self):
        user = UserFactory()
        info = serialize_user(user)
        assert_is_instance(info, dict)
        assert_equal(info['name'], user.fullname)
        assert_equal(info['emails'], user.emails)
        assert_equal(info['last_login'], user.date_last_login)
        assert_equal(len(info['nodes']), 0)

    def test_serialize_simple_node(self):
        node = NodeFactory()
        info = serialize_simple_node(node)
        assert_is_instance(info, dict)
        assert_equal(info['id'], node._id)
        assert_equal(info['title'], node.title)
        assert_equal(info['public'], node.is_public)
        assert_equal(info['number_contributors'], len(node.contributors))
