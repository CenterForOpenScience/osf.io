import mock
from osf.models.admin_log_entry import AdminLogEntry
from admin.nodes.views import (NodeDeleteView, NodeRemoveContributorView,
                               NodeView)
from admin_tests.utilities import setup_log_view, setup_view
from django.test import RequestFactory
from framework.auth import User
from nose import tools as nt
from tests.base import AdminTestCase
from tests.factories import AuthUserFactory, ProjectFactory
from website.project.model import Node, NodeLog


class TestNodeView(AdminTestCase):

    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request)
        with nt.assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        node = ProjectFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        nt.assert_is_instance(res, dict)

    def test_name_data(self):
        node = ProjectFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        nt.assert_equal(res[NodeView.context_object_name], temp_object)


class TestNodeDeleteView(AdminTestCase):
    def setUp(self):
        super(TestNodeDeleteView, self).setUp()
        self.node = ProjectFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = NodeDeleteView()
        self.view = setup_log_view(self.view, self.request,
                                   guid=self.node._id)

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, Node)

    def test_get_context(self):
        res = self.view.get_context_data(object=self.node)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.node._id)

    def test_remove_node(self):
        count = AdminLogEntry.objects.count()
        self.view.delete(self.request)
        self.node.refresh_from_db()
        nt.assert_true(self.node.is_deleted)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_restore_node(self):
        self.view.delete(self.request)
        self.node.refresh_from_db()
        nt.assert_true(self.node.is_deleted)
        count = AdminLogEntry.objects.count()
        self.view.delete(self.request)
        self.node.reload()
        nt.assert_false(self.node.is_deleted)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)


class TestRemoveContributor(AdminTestCase):
    def setUp(self):
        super(TestRemoveContributor, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.user_2 = AuthUserFactory()
        self.node.add_contributor(self.user_2)
        self.node.save()
        self.view = NodeRemoveContributorView()
        self.request = RequestFactory().post('/fake_path')

    def test_get_object(self):
        view = setup_log_view(self.view, self.request, node_id=self.node._id,
                              user_id=self.user._id)
        node, user = view.get_object()
        nt.assert_is_instance(node, Node)
        nt.assert_is_instance(user, User)

    @mock.patch('admin.nodes.views.Node.remove_contributor')
    def test_remove_contributor(self, mock_remove_contributor):
        user_id = self.user_2._id
        node_id = self.node._id
        view = setup_log_view(self.view, self.request, node_id=node_id,
                              user_id=user_id)
        view.delete(self.request)
        mock_remove_contributor.assert_called_with(self.user_2, None, log=False)

    def test_integration_remove_contributor(self):
        nt.assert_in(self.user_2, self.node.contributors)
        view = setup_log_view(self.view, self.request, node_id=self.node._id,
                              user_id=self.user_2._id)
        count = AdminLogEntry.objects.count()
        view.delete(self.request)
        nt.assert_not_in(self.user_2, self.node.contributors)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_do_not_remove_last_admin(self):
        nt.assert_equal(
            len(list(self.node.get_admin_contributors(self.node.contributors))),
            1
        )
        view = setup_log_view(self.view, self.request, node_id=self.node._id,
                              user_id=self.user._id)
        count = AdminLogEntry.objects.count()
        view.delete(self.request)
        self.node.reload()  # Reloads instance to show that nothing was removed
        nt.assert_equal(len(list(self.node.contributors)), 2)
        nt.assert_equal(
            len(list(self.node.get_admin_contributors(self.node.contributors))),
            1
        )
        nt.assert_equal(AdminLogEntry.objects.count(), count)

    def test_no_log(self):
        view = setup_log_view(self.view, self.request, node_id=self.node._id,
                              user_id=self.user_2._id)
        view.delete(self.request)
        nt.assert_not_equal(self.node.logs.latest().action, NodeLog.CONTRIB_REMOVED)
