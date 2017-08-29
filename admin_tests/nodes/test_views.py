import mock

from osf.models import AdminLogEntry, OSFUser, Node, NodeLog
from admin.nodes.views import (
    NodeDeleteView,
    NodeRemoveContributorView,
    NodeView,
    NodeReindexShare,
    NodeReindexElastic,
    NodeFlaggedSpamList,
    NodeKnownSpamList,
    NodeKnownHamList,
)
from admin_tests.utilities import setup_log_view, setup_view

from nose import tools as nt
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory


class TestNodeView(AdminTestCase):

    def test_get_flagged_spam(self):
        user = AuthUserFactory()
        user.is_superuser = True
        user.save()
        request = RequestFactory().get(reverse('nodes:flagged-spam'))
        request.user = user
        response = NodeFlaggedSpamList.as_view()(request)
        nt.assert_equal(response.status_code, 200)

    def test_get_known_spam(self):
        user = AuthUserFactory()
        user.is_superuser = True
        user.save()
        request = RequestFactory().get(reverse('nodes:known-spam'))
        request.user = user
        response = NodeKnownSpamList.as_view()(request)
        nt.assert_equal(response.status_code, 200)

    def test_get_known_ham(self):
        user = AuthUserFactory()
        user.is_superuser = True
        user.save()
        request = RequestFactory().get(reverse('nodes:known-ham'))
        request.user = user
        response = NodeKnownHamList.as_view()(request)
        nt.assert_equal(response.status_code, 200)

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

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        node = ProjectFactory()
        guid = node._id
        request = RequestFactory().get(reverse('nodes:node', kwargs={'guid': guid}))
        request.user = user

        with nt.assert_raises(PermissionDenied):
            NodeView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        node = ProjectFactory()
        guid = node._id

        change_permission = Permission.objects.get(codename='view_node')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('nodes:node', kwargs={'guid': guid}))
        request.user = user

        response = NodeView.as_view()(request, guid=guid)
        nt.assert_equal(response.status_code, 200)


class TestNodeDeleteView(AdminTestCase):
    def setUp(self):
        super(TestNodeDeleteView, self).setUp()
        self.node = ProjectFactory()
        self.request = RequestFactory().post('/fake_path')
        self.plain_view = NodeDeleteView
        self.view = setup_log_view(self.plain_view(), self.request,
                                   guid=self.node._id)

        self.url = reverse('nodes:remove', kwargs={'guid': self.node._id})

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

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        guid = self.node._id
        request = RequestFactory().get(self.url)
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.plain_view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        guid = self.node._id

        change_permission = Permission.objects.get(codename='delete_node')
        view_permission = Permission.objects.get(codename='view_node')
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request, guid=guid)
        nt.assert_equal(response.status_code, 200)


class TestRemoveContributor(AdminTestCase):
    def setUp(self):
        super(TestRemoveContributor, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.user_2 = AuthUserFactory()
        self.node.add_contributor(self.user_2)
        self.node.save()
        self.view = NodeRemoveContributorView
        self.request = RequestFactory().post('/fake_path')
        self.url = reverse('nodes:remove_user', kwargs={'node_id': self.node._id, 'user_id': self.user._id})

    def test_get_object(self):
        view = setup_log_view(self.view(), self.request, node_id=self.node._id,
                              user_id=self.user._id)
        node, user = view.get_object()
        nt.assert_is_instance(node, Node)
        nt.assert_is_instance(user, OSFUser)

    @mock.patch('admin.nodes.views.Node.remove_contributor')
    def test_remove_contributor(self, mock_remove_contributor):
        user_id = self.user_2._id
        node_id = self.node._id
        view = setup_log_view(self.view(), self.request, node_id=node_id,
                              user_id=user_id)
        view.delete(self.request)
        mock_remove_contributor.assert_called_with(self.user_2, None, log=False)

    def test_integration_remove_contributor(self):
        nt.assert_in(self.user_2, self.node.contributors)
        view = setup_log_view(self.view(), self.request, node_id=self.node._id,
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
        view = setup_log_view(self.view(), self.request, node_id=self.node._id,
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
        view = setup_log_view(self.view(), self.request, node_id=self.node._id,
                              user_id=self.user_2._id)
        view.delete(self.request)
        nt.assert_not_equal(self.node.logs.latest().action, NodeLog.CONTRIB_REMOVED)

    def test_no_user_permissions_raises_error(self):
        guid = self.node._id
        request = RequestFactory().get(self.url)
        request.user = self.user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, node_id=guid, user_id=self.user)

    def test_correct_view_permissions(self):
        change_permission = Permission.objects.get(codename='change_node')
        view_permission = Permission.objects.get(codename='view_node')
        self.user.user_permissions.add(change_permission)
        self.user.user_permissions.add(view_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request, node_id=self.node._id, user_id=self.user._id)
        nt.assert_equal(response.status_code, 200)


class TestNodeReindex(AdminTestCase):
    def setUp(self):
        super(TestNodeReindex, self).setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.node, creator=self.user)

    @mock.patch('website.project.tasks.format_node')
    @mock.patch('website.project.tasks.format_registration')
    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_reindex_node_share(self, mock_update_share, mock_format_registration, mock_format_node):
        count = AdminLogEntry.objects.count()
        view = NodeReindexShare()
        view = setup_log_view(view, self.request, guid=self.node._id)
        view.delete(self.request)

        nt.assert_true(mock_update_share.called)
        nt.assert_true(mock_format_node.called)
        nt.assert_false(mock_format_registration.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    @mock.patch('website.project.tasks.format_node')
    @mock.patch('website.project.tasks.format_registration')
    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_reindex_registration_share(self, mock_update_share, mock_format_registration, mock_format_node):
        count = AdminLogEntry.objects.count()
        view = NodeReindexShare()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        view.delete(self.request)

        nt.assert_true(mock_update_share.called)
        nt.assert_false(mock_format_node.called)
        nt.assert_true(mock_format_registration.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    @mock.patch('website.search.search.update_node')
    @mock.patch('website.search.elastic_search.bulk_update_nodes')
    def test_reindex_node_elastic(self, mock_update_search, mock_bulk_update_nodes):
        count = AdminLogEntry.objects.count()
        view = NodeReindexElastic()
        view = setup_log_view(view, self.request, guid=self.node._id)
        view.delete(self.request)

        nt.assert_true(mock_update_search.called)
        nt.assert_true(mock_bulk_update_nodes.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    @mock.patch('website.search.search.update_node')
    @mock.patch('website.search.elastic_search.bulk_update_nodes')
    def test_reindex_registration_elastic(self, mock_update_search, mock_bulk_update_nodes):
        count = AdminLogEntry.objects.count()
        view = NodeReindexElastic()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        view.delete(self.request)

        nt.assert_true(mock_update_search.called)
        nt.assert_true(mock_bulk_update_nodes.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)
