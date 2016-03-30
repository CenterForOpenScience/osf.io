from django.test import RequestFactory
from nose import tools as nt

from tests.base import AdminTestCase
from tests.factories import NodeFactory
from admin_tests.utilities import setup_view
from admin_tests.factories import UserFactory

from admin.nodes.views import (
    NodeView,
    remove_node,
    restore_node,
)


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
        self.request.user = UserFactory()

    def test_remove_node(self):
        remove_node(self.request, self.node._id)
        nt.assert_true(self.node.is_deleted)

    def test_restore_node(self):
        remove_node(self.request, self.node._id)
        nt.assert_true(self.node.is_deleted)
        restore_node(self.request, self.node._id)
        nt.assert_false(self.node.is_deleted)
