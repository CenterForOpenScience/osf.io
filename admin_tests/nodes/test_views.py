import datetime as dt
import pytest
from unittest import mock
import pytz
import datetime

from osf.models import AdminLogEntry, NodeLog, AbstractNode
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
from api_tests.share._utils import mock_update_share
from website import settings
from django.utils import timezone
from django.test import RequestFactory
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from framework.auth.core import Auth

from tests.base import AdminTestCase
from osf_tests.factories import UserFactory, AuthUserFactory, ProjectFactory, RegistrationFactory


def patch_messages(request):
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)


class TestNodeView(AdminTestCase):

    def test_get_flagged_spam(self):
        user = AuthUserFactory()
        user.is_superuser = True
        user.save()
        request = RequestFactory().get(reverse('nodes:flagged-spam'))
        request.user = user
        response = NodeFlaggedSpamList.as_view()(request)
        assert response.status_code == 200

    def test_get_known_spam(self):
        user = AuthUserFactory()
        user.is_superuser = True
        user.save()
        request = RequestFactory().get(reverse('nodes:known-spam'))
        request.user = user
        response = NodeKnownSpamList.as_view()(request)
        assert response.status_code == 200

    def test_get_known_ham(self):
        user = AuthUserFactory()
        user.is_superuser = True
        user.save()
        request = RequestFactory().get(reverse('nodes:known-ham'))
        request.user = user
        response = NodeKnownHamList.as_view()(request)
        assert response.status_code == 200

    def test_name_data(self):
        node = ProjectFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()['node']
        assert res == temp_object

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        node = ProjectFactory()
        guid = node._id
        request = RequestFactory().get(reverse('nodes:node', kwargs={'guid': guid}))
        request.user = user

        with pytest.raises(PermissionDenied):
            NodeView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        node = ProjectFactory()
        guid = node._id

        change_permission = Permission.objects.filter(
            codename='view_node',
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        ).first()
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('nodes:node', kwargs={'guid': guid}))
        request.user = user

        response = NodeView.as_view()(request, guid=guid)
        assert response.status_code == 200


class TestNodeDeleteView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.request = RequestFactory().post('/fake_path')
        self.plain_view = NodeDeleteView
        self.view = setup_log_view(self.plain_view(), self.request, guid=self.node._id)
        self.url = reverse('nodes:remove', kwargs={'guid': self.node._id})

    def test_remove_node(self):
        count = AdminLogEntry.objects.count()
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.view.post(self.request)
        self.node.refresh_from_db()
        assert self.node.is_deleted
        assert AdminLogEntry.objects.count() == count + 1
        assert self.node.deleted == mock_now

    def test_restore_node(self):
        self.view.post(self.request)
        self.node.refresh_from_db()
        assert self.node.is_deleted
        assert self.node.deleted is not None
        count = AdminLogEntry.objects.count()
        self.view.post(self.request)
        self.node.reload()
        assert not self.node.is_deleted
        assert self.node.deleted is None
        assert AdminLogEntry.objects.count() == count + 1

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        guid = self.node._id
        request = RequestFactory().get(self.url)
        request.user = user

        with pytest.raises(PermissionDenied):
            self.plain_view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        guid = self.node._id

        change_permission = Permission.objects.get(codename='delete_node')
        view_permission = Permission.objects.filter(
            codename='view_node',
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        ).first()
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().post(self.url)
        patch_messages(request)
        request.user = user

        response = self.plain_view.as_view()(request, guid=guid)
        assert response.status_code == 302


class TestRemoveContributor(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.user_2 = AuthUserFactory()
        self.node.add_contributor(self.user_2)
        self.node.save()
        self.view = NodeRemoveContributorView
        self.request = RequestFactory().post('/fake_path')
        self.url = reverse('nodes:remove-user', kwargs={'guid': self.node._id, 'user_id': self.user.id})

    def test_remove_contributor(self):
        user_id = self.user_2.id
        node_id = self.node._id
        view = setup_log_view(self.view(), self.request, guid=node_id, user_id=user_id)
        view.post(self.request)
        assert not self.node.contributors.filter(id=user_id)

    def test_integration_remove_contributor(self):
        patch_messages(self.request)
        assert self.user_2 in self.node.contributors
        view = setup_log_view(self.view(), self.request, guid=self.node._id, user_id=self.user_2.id)
        count = AdminLogEntry.objects.count()
        view.post(self.request)
        assert self.user_2 not in self.node.contributors
        assert AdminLogEntry.objects.count() == count + 1

    def test_do_not_remove_last_admin(self):
        patch_messages(self.request)
        assert len(list(self.node.get_admin_contributors(self.node.contributors))) == 1
        view = setup_log_view(self.view(), self.request, guid=self.node._id, user_id=self.user.id)
        count = AdminLogEntry.objects.count()
        view.post(self.request)
        self.node.reload()  # Reloads instance to show that nothing was removed
        assert len(list(self.node.contributors)) == 2
        assert len(list(self.node.get_admin_contributors(self.node.contributors))) == 1
        assert AdminLogEntry.objects.count() == count

    def test_no_log(self):
        view = setup_log_view(self.view(), self.request, guid=self.node._id, user_id=self.user_2.id)
        view.post(self.request)
        assert self.node.logs.latest().action != NodeLog.CONTRIB_REMOVED

    def test_no_user_permissions_raises_error(self):
        guid = self.node._id
        request = RequestFactory().get(self.url)
        request.user = self.user

        with pytest.raises(PermissionDenied):
            self.view.as_view()(request, guid=guid, user_id=self.user)

    def test_correct_view_permissions(self):
        change_permission = Permission.objects.get(codename='change_node')
        view_permission = Permission.objects.filter(
            codename='view_node',
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        ).first()
        self.user.user_permissions.add(change_permission)
        self.user.user_permissions.add(view_permission)
        self.user.save()

        request = RequestFactory().post(self.url)
        patch_messages(request)
        request.user = self.user

        response = self.view.as_view()(request, guid=self.node._id, user_id=self.user.id)
        assert response.status_code == 302


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
class TestNodeReindex(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.node, creator=self.user)

    def test_reindex_node_share(self):
        count = AdminLogEntry.objects.count()
        view = NodeReindexShare()
        view = setup_log_view(view, self.request, guid=self.node._id)
        with mock_update_share() as _shmock:
            view.post(self.request)
            _shmock.assert_called_once_with(self.node)
        assert AdminLogEntry.objects.count() == count + 1

    def test_reindex_registration_share(self):
        count = AdminLogEntry.objects.count()
        view = NodeReindexShare()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        with mock_update_share() as _shmock:
            view.post(self.request)
            _shmock.assert_called_once_with(self.registration)
        assert AdminLogEntry.objects.count() == count + 1

    @mock.patch('website.search.search.update_node')
    def test_reindex_node_elastic(self, mock_update_node):
        count = AdminLogEntry.objects.count()
        view = NodeReindexElastic()
        view = setup_log_view(view, self.request, guid=self.node._id)
        view.post(self.request)

        assert mock_update_node.called
        assert AdminLogEntry.objects.count() == count + 1

    @mock.patch('website.search.search.update_node')
    def test_reindex_registration_elastic(self, mock_update_node):
        count = AdminLogEntry.objects.count()
        view = NodeReindexElastic()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        view.post(self.request)

        assert mock_update_node.called
        assert AdminLogEntry.objects.count() == count + 1

class TestNodeConfirmHamView(AdminTestCase):
    def setUp(self):
        super().setUp()

        self.request = RequestFactory().post('/fake_path')
        self.user = AuthUserFactory()

        self.node = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(creator=self.user)

    def test_confirm_node_as_ham(self):
        view = NodeConfirmHamView()
        view = setup_log_view(view, self.request, guid=self.node._id)
        view.post(self.request)

        self.node.refresh_from_db()
        assert self.node.spam_status == 4

    def test_confirm_registration_as_ham(self):
        view = NodeConfirmHamView()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        resp = view.post(self.request)

        assert resp.status_code == 302

        self.registration.refresh_from_db()
        assert not self.registration.is_public
        assert self.registration.spam_status == 4


class TestAdminNodeLogView(AdminTestCase):

    def setUp(self):
        super().setUp()

        self.request = RequestFactory().post('/fake_path')
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.node = ProjectFactory(creator=self.user)

    def test_get_queryset(self):

        self.node.set_title('New Title', auth=self.auth, save=True)

        view = AdminNodeLogView()
        view = setup_log_view(view, self.request, guid=self.node._id)

        logs = view.get_queryset()

        log_entry = logs.last()
        assert log_entry.action == 'edit_title'
        assert log_entry.params['title_new'] == 'New Title'


class TestRestartStuckRegistrationsView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user, archive=True)
        self.registration.save()
        self.view = RestartStuckRegistrationsView
        self.request = RequestFactory().post('/fake_path')

    def test_get_object(self):
        view = RestartStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)

        assert self.registration == view.get_object()

    def test_restart_stuck_registration(self):
        # Prevents circular import that prevents admin app from starting up
        from django.contrib.messages.storage.fallback import FallbackStorage

        view = RestartStuckRegistrationsView()
        view = setup_log_view(view, self.request, guid=self.registration._id)
        assert self.registration.archive_job.status == 'INITIATED'

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)

        view.post(self.request)

        assert self.registration.archive_job.status == 'SUCCESS'


class TestRemoveStuckRegistrationsView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user, archive=True)
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

        assert self.registration == view.get_object()

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
        assert self.registration.is_deleted
        assert self.registration.deleted is not None

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
        assert self.registration.is_deleted
        assert self.registration.deleted is not None
