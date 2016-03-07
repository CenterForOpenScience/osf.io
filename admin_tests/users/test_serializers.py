from nose import tools as nt

from tests.base import AdminTestCase
from tests.factories import NodeFactory, AuthUserFactory

from admin.users.serializers import serialize_user, serialize_simple_node


class TestUserSerializers(AdminTestCase):
    def test_serialize_user(self):
        user = AuthUserFactory()
        info = serialize_user(user)
        nt.assert_is_instance(info, dict)
        nt.assert_equal(info['name'], user.fullname)
        nt.assert_equal(info['id'], user._id)
        nt.assert_equal(info['emails'], user.emails)
        nt.assert_equal(info['last_login'], user.date_last_login)
        nt.assert_equal(len(info['nodes']), 0)

    def test_serialize_two_factor(self):
        user = AuthUserFactory()
        info = serialize_user(user)
        nt.assert_false(info['two_factor'])
        user.get_or_add_addon('twofactor')
        info = serialize_user(user)
        nt.assert_true(info['two_factor'])

    def test_serialize_simple_node(self):
        node = NodeFactory()
        info = serialize_simple_node(node)
        nt.assert_is_instance(info, dict)
        nt.assert_equal(info['id'], node._id)
        nt.assert_equal(info['title'], node.title)
        nt.assert_equal(info['public'], node.is_public)
        nt.assert_equal(info['number_contributors'], len(node.contributors))
