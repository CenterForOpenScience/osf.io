import datetime as dt
import pytest
from unittest import mock
import pytz
import datetime

from django.utils import timezone
from django.test import RequestFactory
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from osf.models import (
    AdminLogEntry,
    NodeLog,
    AbstractNode,
    RegistrationApproval,
    Embargo,
    SchemaResponse,
    DraftRegistration,
)
from admin.nodes.views import (
    NodeConfirmSpamView,
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
    RemoveStuckRegistrationsView,
    CheckArchiveStatusRegistrationsView,
    ForceArchiveRegistrationsView,
    ApprovalBacklogListView,
    ConfirmApproveBacklogView
)
from admin_tests.utilities import setup_log_view, setup_view, handle_post_view_request
from api_tests.share._utils import mock_update_share
from website import settings
from framework.auth.core import Auth

from tests.base import AdminTestCase
from osf_tests.factories import (
    UserFactory,
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    RegistrationApprovalFactory,
    RegistrationProviderFactory,
    DraftRegistrationFactory,
    get_default_metaschema
)
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates
from osf.utils import permissions
from osf.exceptions import NodeStateError


from website.settings import REGISTRATION_APPROVAL_TIME


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

    def test_node_spam_ham_workflow_if_node_is_private(self):
        superuser = AuthUserFactory()
        superuser.is_superuser = True
        node = ProjectFactory()
        guid = node._id
        request = RequestFactory().post('/fake_path')
        request.user = superuser
        node = handle_post_view_request(request, NodeConfirmSpamView(), node, guid)
        assert not node.is_public
        node = handle_post_view_request(request, NodeConfirmHamView(), node, guid)
        assert not node.is_public

    def test_node_spam_ham_workflow_if_node_is_public(self):
        superuser = AuthUserFactory()
        superuser.is_superuser = True
        node = ProjectFactory()
        node.set_privacy('public')
        guid = node._id
        request = RequestFactory().post('/fake_path')
        request.user = superuser
        node = handle_post_view_request(request, NodeConfirmSpamView(), node, guid)
        assert not node.is_public
        node = handle_post_view_request(request, NodeConfirmHamView(), node, guid)
        assert node.is_public


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


class TestCheckArchiveStatusRegistrationsView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.view = CheckArchiveStatusRegistrationsView
        self.request = RequestFactory().post('/fake_path')

    def test_check_archive_status(self):
        from django.contrib.messages.storage.fallback import FallbackStorage

        registration = RegistrationFactory(creator=self.user, archive=True)
        view = setup_log_view(self.view(), self.request, guid=registration._id)

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)

        view.get(self.request)

        assert not registration.archived
        assert f'Registration {registration._id} is not stuck in archiving' in [m.message for m in messages]


class TestForceArchiveRegistrationsView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user, archive=True)
        self.registration.save()
        self.view = ForceArchiveRegistrationsView
        self.request = RequestFactory().post('/fake_path')

    def test_get_object(self):
        view = setup_log_view(self.view(), self.request, guid=self.registration._id)

        assert self.registration == view.get_object()

    def test_force_archive_registration(self):
        # Prevents circular import that prevents admin app from starting up
        from django.contrib.messages.storage.fallback import FallbackStorage

        view = setup_log_view(self.view(), self.request, guid=self.registration._id)

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)

        view.post(self.request)

        assert self.registration.archive_job.status == 'SUCCESS'

    def test_force_archive_registration_dry_mode(self):
        # Prevents circular import that prevents admin app from starting up
        from django.contrib.messages.storage.fallback import FallbackStorage

        request = RequestFactory().post('/fake_path', data={'dry_mode': 'true'})
        view = setup_log_view(self.view(), request, guid=self.registration._id)
        assert self.registration.archive_job.status == 'INITIATED'

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        view.post(request)

        assert self.registration.archive_job.status == 'INITIATED'


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


class TestApprovalBacklogListView(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.request = RequestFactory().post('/fake_path')
        self.view = setup_log_view(ApprovalBacklogListView(), self.request)

    def request_approval(self, timedelta, should_display=False):
        now = timezone.now()
        RegistrationApprovalFactory(
            initiation_date=now + timedelta,
            end_date=now + timedelta + REGISTRATION_APPROVAL_TIME
        )
        res = self.view.get(self.request)
        is_displayed_in_queryset = res.context_data['queryset'].exists()
        assert is_displayed_in_queryset is should_display

    def test_not_expired_approvals_are_shown(self):
        # we show all approvals in admin if now <= end_date (approval did not expire)
        # as end_date = initiation_date + REGISTRATION_APPROVAL_TIME
        self.request_approval(timezone.timedelta(days=-3), should_display=False)
        self.request_approval(timezone.timedelta(days=-2), should_display=False)
        self.request_approval(timezone.timedelta(days=-1, hours=-23, minutes=-59), should_display=True)
        self.request_approval(timezone.timedelta(days=-1, hours=-23, minutes=-59, seconds=59), should_display=True)
        self.request_approval(timezone.timedelta(days=-1), should_display=True)
        self.request_approval(timezone.timedelta(minutes=-15), should_display=True)
        self.request_approval(timezone.timedelta(minutes=15), should_display=True)
        self.request_approval(timezone.timedelta(days=1), should_display=True)
        self.request_approval(timezone.timedelta(days=1, hours=23, minutes=59), should_display=True)
        self.request_approval(timezone.timedelta(days=2), should_display=True)
        self.request_approval(timezone.timedelta(days=3), should_display=True)


class TestConfirmApproveBacklogView(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_request_approval_is_approved(self):
        now = timezone.now()
        self.approval = RegistrationApprovalFactory(
            initiation_date=now - timezone.timedelta(days=1),
            end_date=now + timezone.timedelta(days=1)
        )
        assert RegistrationApproval.objects.first().state == RegistrationApproval.UNAPPROVED
        request = RequestFactory().post('/fake_path', data={f'{self.approval._id}': '[on]'})
        view = setup_log_view(ConfirmApproveBacklogView(), request)
        view.post(request)
        assert RegistrationApproval.objects.first().state == RegistrationApproval.APPROVED


class TestRegistrationRevertToDraft(AdminTestCase):

    def _add_contributor(self, registration, permission, contributor):
        registration.add_contributor(
            contributor,
            permissions=permission,
            auth=self.auth,
            save=True
        )

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.node = ProjectFactory(creator=self.user)

        self.contr1 = UserFactory()
        self.contr2 = UserFactory()
        self.contr3 = UserFactory()

        pre_moderation_draft = DraftRegistrationFactory(
            title='pre-moderation-registration',
            description='some description',
            registration_schema=get_default_metaschema(),
            provider=RegistrationProviderFactory(reviews_workflow='pre-moderation'),
            creator=self.user
        )
        self._add_contributor(pre_moderation_draft, permissions.ADMIN, self.contr1)
        self._add_contributor(pre_moderation_draft, permissions.ADMIN, self.contr2)
        self._add_contributor(pre_moderation_draft, permissions.ADMIN, self.contr3)
        pre_moderation_draft.register(auth=self.auth, save=True)
        self.pre_moderation_registration = pre_moderation_draft.registered_node

        post_moderation_draft = DraftRegistrationFactory(
            title='post-moderation-registration',
            description='some description',
            registration_schema=get_default_metaschema(),
            provider=RegistrationProviderFactory(reviews_workflow='post-moderation'),
            creator=self.user
        )
        self._add_contributor(post_moderation_draft, permissions.ADMIN, self.contr1)
        self._add_contributor(post_moderation_draft, permissions.ADMIN, self.contr2)
        self._add_contributor(post_moderation_draft, permissions.ADMIN, self.contr3)
        post_moderation_draft.register(auth=self.auth, save=True)
        self.post_moderation_registration = post_moderation_draft.registered_node

        no_moderation_draft = DraftRegistrationFactory(
            title='no-moderation-registration',
            description='some description',
            registration_schema=get_default_metaschema(),
            creator=self.user
        )
        self._add_contributor(no_moderation_draft, permissions.ADMIN, self.contr1)
        self._add_contributor(no_moderation_draft, permissions.ADMIN, self.contr2)
        self._add_contributor(no_moderation_draft, permissions.ADMIN, self.contr3)
        no_moderation_draft.add_tag('tag1', auth=self.auth, save=True)
        no_moderation_draft.add_tag('tag2', auth=self.auth, save=True)
        no_moderation_draft.register(auth=self.auth, save=True)
        self.registration = no_moderation_draft.registered_node

    def get_current_version(self, registration):
        return registration.schema_responses.order_by('-created').first()

    def create_new_version(self, registration, justification=None):
        SchemaResponse.create_from_previous_response(
            initiator=registration.creator,
            previous_response=self.get_current_version(registration),
            justification=justification or 'new update'
        )

    def approve_version(self, version):
        version.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        version.save()

    def test_cannot_revert_updated_and_approved_registration_new_version(self):
        self.approve_version(self.get_current_version(self.registration))
        self.create_new_version(self.registration)
        self.approve_version(self.get_current_version(self.registration))

        # registration has a few versions including the root
        assert self.registration.schema_responses.count() == 2
        with self.assertRaisesMessage(NodeStateError, 'Registration has an approved update thus cannot be reverted to draft'):
            self.registration.to_draft()

    def test_cannot_revert_approved_by_moderator_registration_in_pre_moderation(self):
        self.pre_moderation_registration.moderation_state = RegistrationModerationStates.ACCEPTED.db_name
        self.pre_moderation_registration.save()

        with self.assertRaisesMessage(NodeStateError, 'Registration was approved by moderator thus cannot be reverted to draft'):
            self.pre_moderation_registration.to_draft()

    def test_cannot_revert_approved_by_moderator_registration_in_post_moderation(self):
        self.post_moderation_registration.moderation_state = RegistrationModerationStates.ACCEPTED.db_name
        self.post_moderation_registration.save()

        with self.assertRaisesMessage(NodeStateError, 'Registration was approved by moderator thus cannot be reverted to draft'):
            self.post_moderation_registration.to_draft()

    def test_cannot_revert_registration_with_minted_doi(self):
        self.registration.set_identifier_value('doi', value='some_doi')
        with self.assertRaisesMessage(ValidationError, 'Registration with minted DOI cannot be reverted to draft state'):
            self.registration.to_draft()

    def test_cannot_revert_registration_after_some_updates_but_allow_updates_is_false(self):
        # registration provider has allow_updates attribute that either allows users update registration or not
        # so if user created a new version while allow_updates=True and this attribute was updated to False
        # we still consider this registration as updated

        self.registration.provider.allow_updates = True
        self.registration.provider.save()

        assert self.registration.provider.allow_updates

        self.approve_version(self.get_current_version(self.registration))
        self.create_new_version(self.registration)
        self.approve_version(self.get_current_version(self.registration))

        self.registration.provider.allow_updates = False
        self.registration.provider.save()

        with self.assertRaisesMessage(NodeStateError, 'Registration has an approved update thus cannot be reverted to draft'):
            self.registration.to_draft()

    def test_can_revert_registration_without_updates_to_draft(self):
        self.approve_version(self.get_current_version(self.registration))
        from_draft = DraftRegistration.objects.get(registered_node=self.registration)
        assert from_draft.deleted is None
        assert from_draft.registered_node == self.registration

        self.registration.to_draft()
        from_draft.reload()

        # draft instance isn't linked to the registered version
        assert from_draft.registered_node is None
        assert from_draft.deleted is None
        # registration is deleted
        assert self.registration.deleted is not None

    def test_can_revert_registration_with_unapproved_update_to_draft(self):
        self.approve_version(self.get_current_version(self.registration))
        self.create_new_version(self.registration)
        from_draft = DraftRegistration.objects.get(registered_node=self.registration)

        latest_version = self.registration.schema_responses.first()
        assert latest_version.reviews_state == ApprovalStates.IN_PROGRESS.db_name

        self.registration.to_draft()
        from_draft.reload()

        assert from_draft.deleted is None
        assert from_draft.registered_node is None

    def test_all_previous_data_is_restored_after_revertion(self):
        self.approve_version(self.get_current_version(self.registration))

        draft = DraftRegistration.objects.get(registered_node=self.registration)

        assert draft.title == 'no-moderation-registration'
        assert draft.description == 'some description'
        assert draft.registration_schema == get_default_metaschema()
        assert draft.creator == self.user
        # 3 contributors + creator by default
        assert draft.contributors.count() == 4
        assert draft.tags.count() == 2

        self.registration.to_draft()
        draft.reload()
        self.registration.reload()

        assert draft.registered_node is None
        assert self.registration.deleted is not None
        assert draft.title == 'no-moderation-registration'
        assert draft.description == 'some description'
        assert draft.registration_schema == get_default_metaschema()
        assert draft.creator == self.user
        assert draft.contributors.count() == 4
        assert draft.tags.count() == 2

    def test_contributors_approvals_are_reset_after_revertion(self):
        contributors = self.pre_moderation_registration.contributors.all()
        for contributor in contributors:
            self.pre_moderation_registration.require_approval(contributor)

        assert self.pre_moderation_registration.sanction.approval_stage is ApprovalStates.UNAPPROVED

        for contributor in contributors:
            self.pre_moderation_registration.sanction.approve(
                user=contributor,
                token=self.pre_moderation_registration.sanction.approval_state[contributor._id]['approval_token']
            )
            assert self.pre_moderation_registration.sanction.approval_state[contributor._id]['has_approved'] is True

        self.approve_version(self.get_current_version(self.pre_moderation_registration))

        assert self.pre_moderation_registration.draft_registration.exists()
        assert self.pre_moderation_registration.sanction.approval_stage is ApprovalStates.PENDING_MODERATION

        draft = self.pre_moderation_registration.draft_registration.first()
        self.pre_moderation_registration.to_draft()
        draft.reload()

        # the original has no changes but deleted
        assert self.pre_moderation_registration.sanction.approval_stage is ApprovalStates.PENDING_MODERATION
        assert self.pre_moderation_registration.deleted is not None

        # it's unattached from its draft
        assert draft.registered_node is None

        # draft version is shown and registered again
        draft.register(auth=self.auth, save=True)
        recreated_registration = draft.registered_node

        # ask approvals as it's pre-moderation
        contributors = recreated_registration.contributors.all()
        for contributor in contributors:
            recreated_registration.require_approval(contributor)

        # the new version should have reset approvals and unapproved state
        recreated_registration.sanction.approval_stage is ApprovalStates.UNAPPROVED

        for contributor in contributors:
            recreated_registration.sanction.approval_state[contributor._id]['has_approved'] is False

    def test_revert_node_based_registration(self):
        project = ProjectFactory(
            title='node',
            description='description',
            creator=self.user
        )
        pre_moderation_draft = DraftRegistrationFactory(branched_from=project)
        self._add_contributor(pre_moderation_draft, permissions.ADMIN, self.contr1)
        self._add_contributor(pre_moderation_draft, permissions.ADMIN, self.contr2)
        self._add_contributor(pre_moderation_draft, permissions.ADMIN, self.contr3)
        pre_moderation_draft.register(auth=self.auth, save=True)
        pre_moderation_registration = pre_moderation_draft.registered_node

        assert pre_moderation_registration.branched_from_node
        assert pre_moderation_draft.registered_node is not None

        pre_moderation_registration.to_draft()
        pre_moderation_draft.reload()

        assert pre_moderation_draft.registered_node is None
        assert pre_moderation_draft.title == 'node'
        assert pre_moderation_draft.description == 'description'

    def test_can_revert_embargo_registration_to_draft(self):
        no_moderation_draft = DraftRegistrationFactory(
            title='embargo-registration',
            description='some description',
            registration_schema=get_default_metaschema(),
            creator=self.user
        )
        no_moderation_draft.register(auth=self.auth, save=True)
        self.registration = no_moderation_draft.registered_node

        # embargo is created when draft registration is registered, so it's possible to do for
        # registration only
        self.registration._initiate_embargo(
            user=self.user,
            end_date=timezone.now() + datetime.timedelta(days=3)
        )

        assert isinstance(self.registration.sanction, Embargo)

        self.registration.to_draft()
        self.registration.reload()

        # re-register draft, thus no embargo should be present
        no_moderation_draft.register(auth=self.auth, save=True)
        self.registration = no_moderation_draft.registered_node

        assert self.registration.sanction is None

    def test_embargo_is_reset_after_revertion(self):
        no_moderation_draft = DraftRegistrationFactory(
            title='embargo-registration',
            description='some description',
            registration_schema=get_default_metaschema(),
            creator=self.user
        )
        no_moderation_draft.register(auth=self.auth, save=True)
        self.registration = no_moderation_draft.registered_node

        self.registration._initiate_embargo(
            user=self.user,
            end_date=timezone.now() + datetime.timedelta(days=3)
        )

        assert isinstance(self.registration.sanction, Embargo)

        self.registration.sanction.approvals_machine.set_state(ApprovalStates.COMPLETED)
        assert self.registration.sanction.approvals_machine.get_current_state()._name == ApprovalStates.COMPLETED

        self.registration.to_draft()
        self.registration.reload()

        # re-register draft, thus no embargo should be present
        no_moderation_draft.register(auth=self.auth, save=True)
        self.registration = no_moderation_draft.registered_node

        assert self.registration.sanction is None
