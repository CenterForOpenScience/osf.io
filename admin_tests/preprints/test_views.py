import pytest
from unittest import mock

from django.test import RequestFactory
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission, Group, AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage

from tests.base import AdminTestCase
from osf.models import Preprint, PreprintLog, PreprintRequest, NotificationType
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PreprintRequestFactory,
    NodeFactory,
    SubjectFactory,

)
from osf.models.admin_log_entry import AdminLogEntry
from osf.models.spam import SpamStatus
from osf.utils.workflows import DefaultStates, RequestTypes
from osf.utils.permissions import ADMIN

from admin_tests.utilities import setup_view, setup_log_view, handle_post_view_request

from admin.preprints import views
from tests.utils import assert_notification, capture_notifications

pytestmark = pytest.mark.django_db


@pytest.fixture()
def preprint():
    return PreprintFactory()


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def req(user):
    req = RequestFactory().get('/fake_path')
    req.user = user
    return req


def patch_messages(request):
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)

@pytest.mark.urls('admin.base.urls')
class TestPreprintView:

    @pytest.fixture()
    def plain_view(self):
        return views.PreprintProviderChangeView

    @pytest.fixture()
    def view(self, req, plain_view):
        view = plain_view()
        setup_view(view, req)
        return view

    @pytest.fixture()
    def ham_preprint(self):
        ham_preprint = PreprintFactory()
        ham_preprint.spam_status = SpamStatus.HAM
        ham_preprint.save()
        return ham_preprint

    @pytest.fixture()
    def spam_preprint(self):
        spam_preprint = PreprintFactory()
        spam_preprint.spam_status = SpamStatus.SPAM
        spam_preprint.save()
        return spam_preprint

    @pytest.fixture()
    def flagged_preprint(self):
        flagged_preprint = PreprintFactory()
        flagged_preprint.spam_status = SpamStatus.FLAGGED
        flagged_preprint.save()
        return flagged_preprint

    @pytest.fixture()
    def superuser(self):
        superuser = AuthUserFactory()
        superuser.is_superuser = True
        superuser.save()
        return superuser

    def test_get_object(self, req, preprint, plain_view):
        view = setup_view(plain_view(), req, guid=preprint._id)
        res = view.get_object()
        assert isinstance(res, Preprint)

    def test_no_user_permissions_raises_error(self, user, preprint, plain_view):
        request = RequestFactory().get(reverse('preprints:preprint', kwargs={'guid': preprint._id}))
        request.user = user
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(request, guid=preprint._id)

    def test_get_flagged_spam(self, superuser, preprint, ham_preprint, spam_preprint, flagged_preprint):
        request = RequestFactory().get(reverse('preprints:flagged-spam'))
        request.user = superuser
        response = views.PreprintFlaggedSpamList.as_view()(request)
        assert response.status_code == 200

        response_ids = [res._id for res in response.context_data['preprints']]
        assert preprint._id not in response.context_data['preprints'][0]._id
        assert len(response.context_data['preprints']) == 1
        assert flagged_preprint._id in response_ids
        assert ham_preprint._id not in response_ids
        assert spam_preprint._id not in response_ids
        assert preprint._id not in response_ids

    def test_get_known_spam(self, superuser, preprint, ham_preprint, spam_preprint, flagged_preprint):
        request = RequestFactory().get(reverse('preprints:known-spam'))
        request.user = superuser
        response = views.PreprintKnownSpamList.as_view()(request)
        assert response.status_code == 200

        response_ids = [res._id for res in response.context_data['preprints']]
        assert preprint._id not in response.context_data['preprints'][0]._id
        assert len(response.context_data['preprints']) == 1
        assert flagged_preprint._id not in response_ids
        assert ham_preprint._id not in response_ids
        assert spam_preprint._id in response_ids
        assert preprint._id not in response_ids

    def test_get_known_ham(self, superuser, preprint, ham_preprint, spam_preprint, flagged_preprint):
        request = RequestFactory().get(reverse('preprints:known-ham'))
        request.user = superuser
        response = views.PreprintKnownHamList.as_view()(request)
        assert response.status_code == 200

        response_ids = [res._id for res in response.context_data['preprints']]
        assert preprint._id not in response.context_data['preprints'][0]._id
        assert len(response.context_data['preprints']) == 1
        assert flagged_preprint._id not in response_ids
        assert ham_preprint._id in response_ids
        assert spam_preprint._id not in response_ids
        assert preprint._id not in response_ids

    def test_confirm_spam(self, flagged_preprint, superuser, mock_akismet):
        last_logged_before_method_call = flagged_preprint.last_logged
        request = RequestFactory().post('/fake_path')
        request.user = superuser

        view = views.PreprintConfirmSpamView()
        view = setup_view(view, request, guid=flagged_preprint._id)
        view.post(request)

        assert flagged_preprint.is_public
        flagged_preprint.refresh_from_db()

        assert flagged_preprint.is_spam
        assert flagged_preprint.is_spam
        assert not flagged_preprint.is_public
        assert flagged_preprint.logs.first().action == 'confirm_spam'
        assert last_logged_before_method_call == flagged_preprint.last_logged

    def test_confirm_ham(self, preprint, superuser, mock_akismet):
        last_logged_before_method_call = preprint.last_logged
        request = RequestFactory().post('/fake_path')
        request.user = superuser

        view = views.PreprintConfirmHamView()
        view = setup_view(view, request, guid=preprint._id)
        view.post(request)
        preprint.refresh_from_db()

        assert preprint.spam_status == SpamStatus.HAM
        assert preprint.is_public
        assert preprint.logs.first().action == 'confirm_ham'
        assert last_logged_before_method_call == preprint.last_logged

    def test_valid_but_insufficient_view_permissions(self, user, preprint, plain_view):
        view_permission = Permission.objects.get(codename='view_preprint')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('preprints:preprint', kwargs={'guid': preprint._id}))
        request.user = user

        with pytest.raises(PermissionDenied):
            plain_view.as_view()(request, guid=preprint._id)

    def test_change_preprint_provider(self, user, preprint, plain_view):
        change_permission = Permission.objects.get(codename='change_preprint')
        view_permission = Permission.objects.get(codename='view_preprint')
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}))
        request.POST = {'provider': preprint.provider.id}
        request.user = user

        view = plain_view.as_view()
        response = view(request, guid=preprint._id)
        assert response.status_code == 302

    @pytest.fixture
    def provider_one(self):
        return PreprintProviderFactory()

    @pytest.fixture
    def provider_two(self):
        return PreprintProviderFactory()

    @pytest.fixture
    def provider_osf(self):
        return PreprintProviderFactory(_id='osf')

    @pytest.fixture
    def preprint_user(self, user):
        change_permission = Permission.objects.get(codename='change_preprint')
        view_permission = Permission.objects.get(codename='view_preprint')
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        return user

    @pytest.fixture
    def subject_osf(self, provider_osf):
        return SubjectFactory(provider=provider_osf)

    @pytest.fixture
    def subject_one(self, provider_one):
        return SubjectFactory(provider=provider_one)

    def test_change_preprint_provider_subjects_custom_taxonomies(self, plain_view, preprint_user, provider_one, provider_two, subject_one):
        """ Testing that subjects are changed when providers are changed between two custom taxonomies.
        """

        subject_two = SubjectFactory(provider=provider_two, bepress_subject=subject_one.bepress_subject)

        preprint = PreprintFactory(
            subjects=[[subject_one._id]],
            provider=provider_one,
            creator=preprint_user
        )
        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}), data={'provider': provider_two.id})
        request.user = preprint_user
        response = plain_view.as_view()(request, guid=preprint._id)

        assert response.status_code == 302
        preprint.refresh_from_db()
        assert preprint.provider == provider_two
        assert subject_two in preprint.subjects.all()

    def test_change_preprint_provider_subjects_from_osf(self, plain_view, preprint_user, provider_one, provider_osf, subject_osf):
        """ Testing that subjects are changed when a provider is changed from osf using the bepress subject id of the new subject.
        """

        subject_two = SubjectFactory(provider=provider_one,
            bepress_subject=subject_osf)

        preprint = PreprintFactory(subjects=[[subject_osf._id]], provider=provider_osf, creator=preprint_user)
        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}), data={'provider': provider_one.id})
        request.user = preprint_user
        response = plain_view.as_view()(request, guid=preprint._id)

        assert response.status_code == 302
        preprint.refresh_from_db()
        assert preprint.provider == provider_one
        assert subject_two in preprint.subjects.all()

    def test_change_preprint_provider_subjects_to_osf(self, plain_view, preprint_user, provider_one, provider_osf, subject_osf):
        """ Testing that subjects are changed when providers are changed to osf using the bepress subject id of the old subject
        """

        subject_one = SubjectFactory(provider=provider_one,
            bepress_subject=subject_osf)

        preprint = PreprintFactory(subjects=[[subject_one._id]], provider=provider_one, creator=preprint_user)

        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}), data={'provider': provider_osf.id})
        request.user = preprint_user
        response = plain_view.as_view()(request, guid=preprint._id)

        assert response.status_code == 302
        preprint.refresh_from_db()
        assert preprint.provider == provider_osf
        assert subject_osf in preprint.subjects.all()

    def test_change_preprint_provider_subjects_problem_subject(self, plain_view, preprint_user, provider_one, provider_osf, subject_osf):
        """ Testing that subjects are changed when providers are changed and theres no related mapping between subjects, the old subject stays in place.
        """

        preprint = PreprintFactory(subjects=[[subject_osf._id]], provider=provider_osf, creator=preprint_user)
        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}), data={'provider': provider_one.id})
        request.user = preprint_user

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        response = plain_view.as_view()(request, guid=preprint._id)

        assert response.status_code == 302
        preprint.refresh_from_db()
        assert preprint.provider == provider_one
        assert subject_osf in preprint.subjects.all()

    def test_change_preprint_provider_subjects_change_permissions(self, plain_view, preprint_user, provider_one, provider_osf, subject_osf):
        """ Testing that subjects are changed when providers are changed and theres no related mapping between subjects, the old subject stays in place.
        """
        auth_user = AuthUserFactory()
        change_permission = Permission.objects.get(codename='change_preprint')
        view_permission = Permission.objects.get(codename='view_preprint')
        auth_user.user_permissions.add(change_permission)
        auth_user.user_permissions.add(view_permission)

        preprint = PreprintFactory(subjects=[[subject_osf._id]], provider=provider_osf, creator=preprint_user)
        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}), data={'provider': provider_one.id})
        request.user = auth_user

        patch_messages(request)

        response = plain_view.as_view()(request, guid=preprint._id)

        assert response.status_code == 302
        preprint.refresh_from_db()
        assert preprint.provider == provider_one
        assert subject_osf in preprint.subjects.all()

    def test_preprint_spam_ham_workflow_if_preprint_is_public(self, preprint, superuser):
        request = RequestFactory().post('/fake_path')
        request.user = superuser
        preprint = handle_post_view_request(request, views.PreprintConfirmSpamView(), preprint, preprint._id)
        assert not preprint.is_public
        preprint = handle_post_view_request(request, views.PreprintConfirmHamView(), preprint, preprint._id)
        assert preprint.is_public

    def test_preprint_spam_ham_workflow_if_preprint_is_private(self, preprint, superuser):
        preprint.set_privacy('private')
        preprint.refresh_from_db()
        request = RequestFactory().post('/fake_path')
        request.user = superuser
        preprint = handle_post_view_request(request, views.PreprintConfirmSpamView(), preprint, preprint._id)
        assert not preprint.is_public
        preprint = handle_post_view_request(request, views.PreprintConfirmHamView(), preprint, preprint._id)
        assert not preprint.is_public


@pytest.mark.urls('admin.base.urls')
@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
class TestPreprintReindex:

    def test_reindex_preprint_share(self, preprint, req, mock_update_share):
        preprint.provider.access_token = 'totally real access token I bought from a guy wearing a trenchcoat in the summer'
        preprint.provider.save()

        count = AdminLogEntry.objects.count()
        view = views.PreprintReindexShare()
        view = setup_log_view(view, req, guid=preprint._id)
        mock_update_share.reset_mock()
        view.post(req)
        mock_update_share.assert_called_once_with(preprint)
        assert AdminLogEntry.objects.count() == count + 1

    @mock.patch('website.search.search.update_preprint')
    def test_reindex_preprint_elastic(self, mock_update_search, preprint, req):
        count = AdminLogEntry.objects.count()
        view = views.PreprintReindexElastic()
        view = setup_log_view(view, req, guid=preprint._id)
        view.post(req)

        assert mock_update_search.called
        assert AdminLogEntry.objects.count() == count + 1


class TestPreprintDeleteView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.request = RequestFactory().post('/fake_path')
        self.plain_view = views.PreprintDeleteView
        self.view = setup_log_view(self.plain_view(), self.request,
                                   guid=self.preprint._id)

        self.url = reverse('preprints:remove', kwargs={'guid': self.preprint._id})

    def test_remove_preprint(self):
        count = AdminLogEntry.objects.count()
        self.view.post(self.request)
        self.preprint.refresh_from_db()
        assert self.preprint.deleted is not None
        assert AdminLogEntry.objects.count() == count + 1

    def test_restore_preprint(self):
        self.view.post(self.request)
        self.preprint.refresh_from_db()
        assert self.preprint.deleted is not None
        count = AdminLogEntry.objects.count()
        self.view.post(self.request)
        self.preprint.reload()
        assert self.preprint.deleted is None
        assert AdminLogEntry.objects.count() == count + 1


class TestRemoveContributor(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.user_2 = AuthUserFactory()
        self.preprint.add_contributor(self.user_2)
        self.preprint.save()
        self.view = views.PreprintRemoveContributorView
        self.request = RequestFactory().post('/fake_path')
        self.url = reverse('preprints:remove-user', kwargs={'guid': self.preprint._id, 'user_id': self.user._id})

    def test_remove_contributor(self):
        user_id = self.user_2.id
        preprint_id = self.preprint._id
        view = setup_log_view(
            self.view(),
            self.request,
            guid=preprint_id,
            user_id=user_id
        )
        view.post(self.request)
        assert not self.preprint.contributors.filter(id=user_id)

    def test_integration_remove_contributor(self):
        assert self.user_2 in self.preprint.contributors
        view = setup_log_view(
            self.view(),
            self.request,
            guid=self.preprint._id,
            user_id=self.user_2.id
        )
        count = AdminLogEntry.objects.count()
        view.post(self.request)
        assert self.user_2 not in self.preprint.contributors
        assert AdminLogEntry.objects.count() == count + 1

    def test_do_not_remove_last_admin(self):
        assert len(list(self.preprint.get_admin_contributors(self.preprint.contributors))) == 1
        view = setup_log_view(
            self.view(),
            self.request,
            guid=self.preprint._id,
            user_id=self.user.id
        )
        count = AdminLogEntry.objects.count()
        patch_messages(self.request)
        view.post(self.request)
        self.preprint.reload()  # Reloads instance to show that nothing was removed
        assert len(list(self.preprint.contributors)) == 2
        assert len(list(self.preprint.get_admin_contributors(self.preprint.contributors))) == 1
        assert AdminLogEntry.objects.count() == count

    def test_no_log(self):
        view = setup_log_view(
            self.view(),
            self.request,
            guid=self.preprint._id,
            user_id=self.user_2.id
        )
        view.post(self.request)
        assert self.preprint.logs.latest().action != PreprintLog.CONTRIB_REMOVED


@pytest.mark.urls('admin.base.urls')
@pytest.mark.django_db
class TestPreprintConfirmHamSpamViews:

    def test_confirm_preprint_as_ham(self, mock_akismet):
        request = RequestFactory().post('/fake_path')
        user = AuthUserFactory()
        preprint = PreprintFactory(creator=user)
        view = views.PreprintConfirmHamView()
        view = setup_log_view(view, request, guid=preprint._id)
        view.post(request)

        preprint.refresh_from_db()
        assert preprint.spam_status == 4

    def test_confirm_preprint_as_spam(self, mock_akismet):
        request = RequestFactory().post('/fake_path')
        user = AuthUserFactory()
        preprint = PreprintFactory(creator=user)
        assert preprint.is_public
        view = views.PreprintConfirmSpamView()
        view = setup_log_view(view, request, guid=preprint._id)
        view.post(request)

        preprint.refresh_from_db()
        assert preprint.spam_status == 2
        assert not preprint.is_public


@pytest.mark.urls('admin.base.urls')
class TestPreprintWithdrawalRequests:

    @pytest.fixture()
    def submitter(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self):
        admin = AuthUserFactory()
        osf_admin = Group.objects.get(name='osf_admin')
        admin.groups.add(osf_admin)
        return admin

    @pytest.fixture()
    def project(self, submitter):
        return NodeFactory(creator=submitter)

    @pytest.fixture()
    def preprint(self, project):
        return PreprintFactory(project=project)

    @pytest.fixture()
    def withdrawal_request(self, preprint, submitter):
        withdrawal_request = PreprintRequestFactory(
            creator=submitter,
            target=preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value,
        )
        withdrawal_request.run_submit(submitter)
        return withdrawal_request

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_can_approve_withdrawal_request(self, mocked_function, withdrawal_request, submitter, preprint, admin):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value
        original_comment = withdrawal_request.comment

        request = RequestFactory().post(reverse('preprints:approve-withdrawal', kwargs={'guid': preprint._id}))
        request.POST = {'action': 'approve'}
        request.user = admin

        with capture_notifications():
            response = views.PreprintApproveWithdrawalRequest.as_view()(request, guid=preprint._id)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()
        assert withdrawal_request.machine_state == DefaultStates.ACCEPTED.value
        assert original_comment == withdrawal_request.target.withdrawal_justification

        # share update is triggered when update "date_withdrawn" and "withdrawal_justification" throughout withdrawal process
        updated_fields = mocked_function.call_args[1]['saved_fields']
        assert 'date_withdrawn' in updated_fields
        assert 'withdrawal_justification' in updated_fields
        assert preprint.SEARCH_UPDATE_FIELDS.intersection(updated_fields)

    def test_can_reject_withdrawal_request(self, withdrawal_request, admin, preprint):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value

        request = RequestFactory().post(reverse('preprints:reject-withdrawal', kwargs={'guid': preprint._id}))
        request.POST = {'action': 'reject'}
        request.user = admin

        with capture_notifications():
            response = views.PreprintRejectWithdrawalRequest.as_view()(request, guid=preprint._id)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()
        assert withdrawal_request.machine_state == DefaultStates.REJECTED.value
        assert not withdrawal_request.target.withdrawal_justification

    def test_can_unwithdraw_preprint(self, withdrawal_request, submitter, preprint, admin):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value
        original_comment = withdrawal_request.comment

        request = RequestFactory().post(reverse('preprints:approve-withdrawal', kwargs={'guid': preprint._id}))
        request.POST = {'action': 'approve'}
        request.user = admin

        with capture_notifications():
            response = views.PreprintApproveWithdrawalRequest.as_view()(request, guid=preprint._id)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()
        assert withdrawal_request.machine_state == DefaultStates.ACCEPTED.value
        assert original_comment == withdrawal_request.target.withdrawal_justification

        # Store PreprintRequest ID before deletion
        withdrawal_request_id = withdrawal_request.id
        request_unwithdraw = RequestFactory().post(reverse('preprints:unwithdraw', kwargs={'guid': preprint._id}))
        request_unwithdraw.user = admin
        response_unwithdraw = views.PreprintUnwithdrawView.as_view()(request_unwithdraw, guid=preprint._id)
        assert response_unwithdraw.status_code == 302

        assert not PreprintRequest.objects.filter(id=withdrawal_request_id).exists()
        preprint.refresh_from_db()
        assert preprint.date_withdrawn is None
        assert preprint.withdrawal_justification == ''

        new_withdrawal_request = PreprintRequestFactory(
            creator=submitter,
            target=preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value,
        )
        new_withdrawal_request.run_submit(submitter)

        assert new_withdrawal_request.machine_state == DefaultStates.PENDING.value
        original_comment = new_withdrawal_request.comment

        new_request = RequestFactory().post(reverse('preprints:approve-withdrawal', kwargs={'guid': preprint._id}))
        new_request.POST = {'action': 'approve'}
        new_request.user = admin

        with capture_notifications():
            response = views.PreprintApproveWithdrawalRequest.as_view()(new_request, guid=preprint._id)
        assert response.status_code == 302

        new_withdrawal_request.refresh_from_db()
        new_withdrawal_request.target.refresh_from_db()
        assert new_withdrawal_request.machine_state == DefaultStates.ACCEPTED.value
        assert original_comment == new_withdrawal_request.target.withdrawal_justification

    def test_can_unwithdraw_preprint_without_moderation_workflow(self, withdrawal_request, submitter, preprint, admin):
        provider = PreprintProviderFactory(reviews_workflow=None)
        preprint = PreprintFactory(project=NodeFactory(creator=submitter), provider=provider)

        withdrawal_request = PreprintRequestFactory(
            creator=admin,
            target=preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(admin)

        with assert_notification(type=NotificationType.Type.PREPRINT_REQUEST_WITHDRAWAL_APPROVED):
            withdrawal_request.run_accept(admin, withdrawal_request.comment)

        assert preprint.machine_state == 'withdrawn'

        request_unwithdraw = RequestFactory().post(reverse('preprints:unwithdraw', kwargs={'guid': preprint._id}))
        request_unwithdraw.user = admin
        response_unwithdraw = views.PreprintUnwithdrawView.as_view()(request_unwithdraw, guid=preprint._id)
        assert response_unwithdraw.status_code == 302

        preprint.refresh_from_db()
        assert preprint.machine_state == DefaultStates.ACCEPTED.value

    def test_can_unwithdraw_preprint_in_pre_moderation(self, withdrawal_request, submitter, preprint, admin):
        provider = PreprintProviderFactory(reviews_workflow='pre-moderation')
        preprint = PreprintFactory(project=NodeFactory(creator=submitter), provider=provider)

        withdrawal_request = PreprintRequestFactory(
            creator=admin,
            target=preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(admin)
        with capture_notifications():
            withdrawal_request.run_accept(admin, withdrawal_request.comment)

        assert preprint.machine_state == 'withdrawn'

        request_unwithdraw = RequestFactory().post(reverse('preprints:unwithdraw', kwargs={'guid': preprint._id}))
        request_unwithdraw.user = admin
        response_unwithdraw = views.PreprintUnwithdrawView.as_view()(request_unwithdraw, guid=preprint._id)
        assert response_unwithdraw.status_code == 302

        preprint.refresh_from_db()
        assert preprint.machine_state == DefaultStates.ACCEPTED.value

    def test_permissions_errors(self, user, submitter):
        # with auth, no permissions
        request = RequestFactory().get(reverse('preprints:withdrawal-requests'))
        request.user = user
        with pytest.raises(PermissionDenied):
            views.PreprintWithdrawalRequestList.as_view()(request)

        # request submitter
        request = RequestFactory().get(reverse('preprints:withdrawal-requests'))
        request.user = submitter
        with pytest.raises(PermissionDenied):
            views.PreprintWithdrawalRequestList.as_view()(request)

        # no auth
        request = RequestFactory().get(reverse('preprints:withdrawal-requests'))
        request.user = AnonymousUser()
        with pytest.raises(PermissionDenied):
            views.PreprintWithdrawalRequestList.as_view()(request)

    def test_osf_admin_has_correct_view_permissions(self, withdrawal_request, admin):
        request = RequestFactory().get(reverse('preprints:withdrawal-requests'))

        request.user = admin
        response = views.PreprintWithdrawalRequestList.as_view()(request)
        assert response.status_code == 200

    @pytest.mark.parametrize('action, final_state', [
        ('approve', DefaultStates.ACCEPTED.value),
        ('reject', DefaultStates.REJECTED.value)])
    def test_approve_reject_on_list_view(self, withdrawal_request, admin, action, final_state):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value
        original_comment = withdrawal_request.comment

        request = RequestFactory().post(reverse('preprints:withdrawal-requests'), {'action': action, withdrawal_request.id: ['on']})
        request.user = admin

        with capture_notifications():
            response = views.PreprintWithdrawalRequestList.as_view()(request)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()

        assert withdrawal_request.machine_state == final_state

        if action == 'approve':
            assert original_comment == withdrawal_request.target.withdrawal_justification
        else:
            assert not withdrawal_request.target.withdrawal_justification


@pytest.mark.urls('admin.base.urls')
@pytest.mark.django_db
class TestPreprintMachineStateView:

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin_user(self):
        admin_user = AuthUserFactory()
        admin_user.is_admin = True
        admin_user.save()
        return admin_user

    @pytest.fixture()
    def req(self, user):
        req = RequestFactory().post('/fake_path')
        req.user = user
        return req

    @pytest.fixture()
    def admin_req(self, admin_user):
        req = RequestFactory().post('/fake_path')
        req.user = admin_user
        return req

    def test_post_changes_machine_state(self, admin_req, preprint):
        new_state = 'new_state'
        admin_req.POST = {'machine_state': new_state}

        view = setup_view(views.PreprintMachineStateView(), admin_req, guid=preprint._id)
        response = view.post(admin_req)

        preprint.refresh_from_db()
        assert preprint.machine_state == new_state
        assert response.status_code == 302

    def test_post_no_change_in_machine_state(self, admin_req, preprint):
        current_state = preprint.machine_state
        admin_req.POST = {'machine_state': current_state}

        view = setup_view(views.PreprintMachineStateView(), admin_req, guid=preprint._id)
        response = view.post(admin_req)

        preprint.refresh_from_db()
        assert preprint.machine_state == current_state
        assert response.status_code == 302

    def test_no_permission_raises_error(self, req, preprint):
        request = RequestFactory().post(reverse('preprints:preprint-machine-state', kwargs={'guid': preprint._id}))
        request.user = req.user
        with pytest.raises(PermissionDenied):
            views.PreprintMachineStateView.as_view()(request, guid=preprint._id)


@pytest.mark.urls('admin.base.urls')
class TestPreprintMakePublishedView:

    @pytest.fixture()
    def plain_view(self):
        return views.PreprintMakePublishedView

    def test_admin_user_can_publish_preprint(self, user, preprint, plain_view):
        admin_group = Group.objects.get(name='osf_admin')
        preprint.is_published = False
        preprint.save()

        # user isn't admin contributor in the preprint
        assert preprint.contributors.filter(id=user.id).exists() is False
        assert preprint.has_permission(user, ADMIN) is False

        request = RequestFactory().post(reverse('preprints:make-published', kwargs={'guid': preprint._id}))
        request.user = user

        admin_group.permissions.add(Permission.objects.get(codename='change_node'))
        user.groups.add(admin_group)

        with capture_notifications():
            plain_view.as_view()(request, guid=preprint._id)
        preprint.reload()

        assert preprint.is_published


@pytest.mark.urls('admin.base.urls')
class TestPreprintReVersionView:

    @pytest.fixture()
    def plain_view(self):
        return views.PreprintReVersion

    def test_admin_user_can_add_new_version_one(self, user, preprint, plain_view):
        # user isn't admin contributor in the preprint
        assert preprint.contributors.filter(id=user.id).exists() is False
        assert preprint.has_permission(user, ADMIN) is False
        assert len(preprint.get_preprint_versions()) == 1

        request = RequestFactory().post(
            reverse('preprints:re-version-preprint',
            kwargs={'guid': preprint._id}),
            data={'file_versions': ['1']}
        )
        request.user = user

        admin_group = Group.objects.get(name='osf_admin')
        admin_group.permissions.add(Permission.objects.get(codename='change_node'))
        user.groups.add(admin_group)

        plain_view.as_view()(request, guid=preprint._id)
        preprint.refresh_from_db()

        assert len(preprint.get_preprint_versions()) == 2
