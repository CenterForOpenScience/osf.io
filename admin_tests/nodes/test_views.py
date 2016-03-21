from django.test import RequestFactory
from nose import tools as nt
import mock

from tests.base import AdminTestCase
from tests.factories import NodeFactory, AuthUserFactory
from admin_tests.utilities import setup_view

from admin.nodes.views import (
    NodeView,
    remove_node,
    restore_node,
    remove_contributor,
)
from website.project.model import NodeLog


class TestNodeView(AdminTestCase):

    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request)
        with nt.assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        node = NodeFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        nt.assert_is_instance(res, dict)

    def test_name_data(self):
        node = NodeFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        nt.assert_equal(res[NodeView.context_object_name], temp_object)


class TestRemoveNode(AdminTestCase):
    def setUp(self):
        super(TestRemoveNode, self).setUp()
        self.node = NodeFactory()
        self.request = RequestFactory().get('/fake_path')

    def test_remove_node(self):
        remove_node(self.request, self.node._id)
        nt.assert_true(self.node.is_deleted)

    def test_restore_node(self):
        remove_node(self.request, self.node._id)
        nt.assert_true(self.node.is_deleted)
        restore_node(self.request, self.node._id)
        nt.assert_false(self.node.is_deleted)


class TestRemoveContributor(AdminTestCase):
    def setUp(self):
        super(TestRemoveContributor, self).setUp()
        self.user = AuthUserFactory()
        self.node = NodeFactory(creator=self.user)
        self.user_2 = AuthUserFactory()
        self.node.add_contributor(self.user_2)
        self.node.save()
        self.request = RequestFactory().get('/fake_path')

    @mock.patch('admin.nodes.views.Node.remove_contributor')
    def test_remove_contributor(self, mock_remove_contributor):
        user_id = self.user_2._id
        node_id = self.node._id
        remove_contributor(self.request, node_id, user_id)
        mock_remove_contributor.assert_called_with(self.user_2, None, log=False)

    def test_integration_remove_contributor(self):
        nt.assert_in(self.user_2, self.node.contributors)
        remove_contributor(self.request, self.node._id, self.user_2._id)
        nt.assert_not_in(self.user_2, self.node.contributors)

    def test_do_not_remove_last_admin(self):
        nt.assert_equal(
            len(list(self.node.get_admin_contributors(self.node.contributors))),
            1
        )
        remove_contributor(self.request, self.node._id, self.user._id)
        self.node.reload()  # Reloads instance to show that nothing was removed
        nt.assert_equal(len(list(self.node.contributors)), 2)
        nt.assert_equal(
            len(list(self.node.get_admin_contributors(self.node.contributors))),
            1
        )

    def test_no_log(self):
        remove_contributor(self.request, self.node._id, self.user_2._id)
        nt.assert_not_equal(self.node.logs[-1].action, NodeLog.CONTRIB_REMOVED)
