import datetime as dt
import pytest
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
    NodeConfirmHamView,
    AdminNodeLogView,
    RestartStuckRegistrationsView,
    RemoveStuckRegistrationsView
)
from admin_tests.utilities import setup_log_view, setup_view
from website import settings
from nose import tools as nt
from django.utils import timezone
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from framework.auth.core import Auth

from tests.base import AdminTestCase
from osf_tests.factories import UserFactory, AuthUserFactory, ProjectFactory, RegistrationFactory


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
        self.url = reverse('nodes:remove_user', kwargs={'guid': self.node._id, 'user_id': self.user._id})

    def test_get_object(self):
        view = setup_log_view(self.view(), self.request, guid=self.node._id,
                              user_id=self.user._id)
        node, user = view.get_object()
        nt.assert_is_instance(node, Node)
        nt.assert_is_instance(user, OSFUser)

    @mock.patch('admin.nodes.views.Node.remove_contributor')
    def test_remove_contributor(self, mock_remove_contributor):
        user_id = self.user_2._id
        node_id = self.node._id
        view = setup_log_view(self.view(), self.request, guid=node_id,
                              user_id=user_id)
        view.delete(self.request)
        mock_remove_contributor.assert_called_with(self.user_2, None, log=False)

    def test_integration_remove_contributor(self):
        nt.assert_in(self.user_2, self.node.contributors)
        view = setup_log_view(self.view(), self.request, guid=self.node._id,
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
        view = setup_log_view(self.view(), self.request, guid=self.node._id,
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
        view = setup_log_view(self.view(), self.request, guid=self.node._id,
                              user_id=self.user_2._id)
        view.delete(self.request)
        nt.assert_not_equal(self.node.logs.latest().action, NodeLog.CONTRIB_REMOVED)

    def test_no_user_permissions_raises_error(self):
        guid = self.node._id
        request = RequestFactory().get(self.url)
        request.user = self.user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, guid=guid, user_id=self.user)

    def test_correct_view_permissions(self):
        change_permission = Permission.objects.get(codename='change_node')
        view_permission = Permission.objects.get(codename='view_node')
        self.user.user_permissions.add(change_permission)
        self.user.user_permissions.add(view_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request, guid=self.node._id, user_id=self.user._id)
        nt.assert_equal(response.status_code, 200)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
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
    def test_reindex_node_elastic(self, mock_update_node):
        count = AdminLogEntry.objects.count()
        view = NodeReindexElastic()
        view = setup_log_view(view, self.request, guid=self.node._id)
        view.delete(self.request)

        nt.assert_true(mock_update_node.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    @mock.patch('website.search.search.update_node')
    def test_reindex_registration_elastic(self, mock_update_node):
        count = AdminLogEntry.objects.count()
        view = NodeReindexElastic()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        view.delete(self.request)

        nt.assert_true(mock_update_node.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

class TestNodeConfirmHamView(AdminTestCase):
    def setUp(self):
        super(TestNodeConfirmHamView, self).setUp()

        self.request = RequestFactory().post('/fake_path')
        self.user = AuthUserFactory()

        self.node = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(creator=self.user)

    def test_confirm_node_as_ham(self):
        view = NodeConfirmHamView()
        view = setup_log_view(view, self.request, guid=self.node._id)
        view.delete(self.request)

        self.node.refresh_from_db()
        nt.assert_true(self.node.spam_status == 4)

    def test_confirm_registration_as_ham(self):
        view = NodeConfirmHamView()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        view.delete(self.request)

        self.registration.refresh_from_db()
        nt.assert_true(self.registration.spam_status == 4)


class TestAdminNodeLogView(AdminTestCase):

    def setUp(self):
        super(TestAdminNodeLogView, self).setUp()

        self.request = RequestFactory().post('/fake_path')
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.node = ProjectFactory(creator=self.user)

    def test_get_object(self):

        view = AdminNodeLogView()
        view = setup_log_view(view, self.request, guid=self.node._id)

        nt.assert_true(self.node, view.get_object())

    def test_get_queryset(self):

        self.node.set_title('New Title', auth=self.auth, save=True)

        view = AdminNodeLogView()
        view = setup_log_view(view, self.request, guid=self.node._id)

        logs = view.get_queryset()

        log_entry = logs.first()
        nt.assert_true(log_entry.action == 'edit_title')
        nt.assert_true(log_entry.params['title_new'] == u'New Title')

    def test_get_context_data(self):

        self.node.set_title('New Title', auth=self.auth, save=True)

        view = AdminNodeLogView()
        view = setup_log_view(view, self.request, guid=self.node._id)

        logs = view.get_context_data()['logs']
        log_entry = logs[0][0]
        log_params = logs[0][1]
        nt.assert_true(log_entry.action == NodeLog.EDITED_TITLE)
        nt.assert_true((u'title_new', u'New Title') in log_params)
        nt.assert_true((u'node', self.node._id) in log_params)

    def test_get_logs_for_children(self):
        """ The "create component" action is actually logged as a create_project action
        for its child with a log parameter 'node' having its guid as a value. We have to ensure
        that all the components a parent has created appear in its admin app logs, so we can't just
         do node.logs.all(), that will leave out component creation.
        """

        component = ProjectFactory(creator=self.user, parent=self.node)
        component.save()

        view = AdminNodeLogView()
        view = setup_log_view(view, self.request, guid=self.node._id)

        logs = view.get_context_data()['logs']
        log_entry = logs[0][0]
        log_params = logs[0][1]

        nt.assert_true(log_entry.action == NodeLog.PROJECT_CREATED)
        nt.assert_true(log_entry.node._id == component._id)
        nt.assert_true(('node', component._id) in log_params)


class TestRestartStuckRegistrationsView(AdminTestCase):
    def setUp(self):
        super(TestRestartStuckRegistrationsView, self).setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.save()
        self.view = RestartStuckRegistrationsView
        self.request = RequestFactory().post('/fake_path')

    def test_get_object(self):
        view = RestartStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)

        nt.assert_true(self.registration, view.get_object())

    def test_restart_stuck_registration(self):
        # Prevents circular import that prevents admin app from starting up
        from django.contrib.messages.storage.fallback import FallbackStorage

        view = RestartStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        nt.assert_equal(self.registration.archive_job.status, u'INITIATED')

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)

        view.post(self.request)

        nt.assert_equal(self.registration.archive_job.status, u'SUCCESS')


class TestRemoveStuckRegistrationsView(AdminTestCase):
    def setUp(self):
        super(TestRemoveStuckRegistrationsView, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        # Make the registration "stuck"
        archive_job = self.registration.archive_job
        archive_job.datetime_initiated = (
            timezone.now() - settings.ARCHIVE_TIMEOUT_TIMEDELTA - dt.timedelta(hours=1)
        )
        archive_job.save()
        self.registration.save()
        self.view = RemoveStuckRegistrationsView
        self.request = RequestFactory().post('/fake_path')

    def test_get_object(self):
        view = RemoveStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)

        nt.assert_true(self.registration, view.get_object())

    def test_remove_stuck_registration(self):
        # Prevents circular import that prevents admin app from starting up
        from django.contrib.messages.storage.fallback import FallbackStorage
        view = RemoveStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)

        view.post(self.request)

        self.registration.refresh_from_db()
        nt.assert_true(self.registration.is_deleted)

    def test_remove_stuck_registration_with_an_addon(self):
        # Prevents circular import that prevents admin app from starting up
        from django.contrib.messages.storage.fallback import FallbackStorage
        self.registration.add_addon('github', auth=Auth(self.user))
        view = RemoveStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)
        view.post(self.request)
        self.registration.refresh_from_db()
        nt.assert_true(self.registration.is_deleted)
