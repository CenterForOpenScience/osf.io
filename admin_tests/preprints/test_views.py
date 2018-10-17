import pytest
import mock

from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission, Group, AnonymousUser

from osf.models import PreprintService
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PreprintRequestFactory,
    NodeFactory,
)
from osf.models.admin_log_entry import AdminLogEntry
from osf.models.spam import SpamStatus
from osf.utils.workflows import DefaultStates, RequestTypes

from admin_tests.utilities import setup_view, setup_log_view

from admin.preprints import views
from admin.preprints.forms import ChangeProviderForm

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

@pytest.mark.urls('admin.base.urls')
class TestPreprintView:

    @pytest.fixture()
    def plain_view(self):
        return views.PreprintView

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

    def test_no_guid(self, view):
        preprint = view.get_object()
        assert preprint is None

    def test_get_object(self, req, preprint, plain_view):
        view = setup_view(plain_view(), req, guid=preprint._id)
        res = view.get_object()
        assert isinstance(res, PreprintService)

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

        response_ids = [res['id'] for res in response.context_data['preprints']]
        assert preprint._id not in response.context_data['preprints'][0]['id']
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

        response_ids = [res['id'] for res in response.context_data['preprints']]
        assert preprint._id not in response.context_data['preprints'][0]['id']
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

        response_ids = [res['id'] for res in response.context_data['preprints']]
        assert preprint._id not in response.context_data['preprints'][0]['id']
        assert len(response.context_data['preprints']) == 1
        assert flagged_preprint._id not in response_ids
        assert ham_preprint._id in response_ids
        assert spam_preprint._id not in response_ids
        assert preprint._id not in response_ids

    def test_confirm_spam(self, flagged_preprint, superuser):
        request = RequestFactory().post('/fake_path')
        request.user = superuser

        view = views.PreprintConfirmSpamView()
        view = setup_view(view, request, guid=flagged_preprint._id)
        view.delete(request)

        assert flagged_preprint.node.is_public

        flagged_preprint.refresh_from_db()
        flagged_preprint.node.refresh_from_db()

        assert flagged_preprint.is_spam
        assert flagged_preprint.node.is_spam
        assert not flagged_preprint.node.is_public

    def test_confirm_ham(self, preprint, superuser):
        request = RequestFactory().post('/fake_path')
        request.user = superuser

        view = views.PreprintConfirmHamView()
        view = setup_view(view, request, guid=preprint._id)
        view.delete(request)

        preprint.refresh_from_db()
        preprint.node.refresh_from_db()

        assert preprint.spam_status == SpamStatus.HAM
        assert preprint.node.spam_status == SpamStatus.HAM
        assert preprint.node.is_public

    def test_correct_view_permissions(self, user, preprint, plain_view):
        view_permission = Permission.objects.get(codename='view_preprintservice')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('preprints:preprint', kwargs={'guid': preprint._id}))
        request.user = user

        response = plain_view.as_view()(request, guid=preprint._id)
        assert response.status_code == 200

    def test_change_preprint_provider_no_permission(self, user, preprint, plain_view):
        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}))
        request.user = user

        with pytest.raises(PermissionDenied):
            plain_view.as_view()(request, guid=preprint._id)

    def test_change_preprint_provider_correct_permission(self, user, preprint, plain_view):
        change_permission = Permission.objects.get(codename='change_preprintservice')
        view_permission = Permission.objects.get(codename='view_preprintservice')
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': preprint._id}))
        request.user = user

        response = plain_view.as_view()(request, guid=preprint._id)
        assert response.status_code == 302

    def test_change_preprint_provider_form(self, plain_view, preprint):
        new_provider = PreprintProviderFactory()
        plain_view.kwargs = {'guid': preprint._id}
        form_data = {
            'provider': new_provider.id
        }
        form = ChangeProviderForm(data=form_data, instance=preprint)
        plain_view().form_valid(form)

        assert preprint.provider == new_provider

@pytest.mark.urls('admin.base.urls')
class TestPreprintFormView:

    @pytest.fixture()
    def view(self):
        return views.PreprintFormView

    @pytest.fixture()
    def url(self):
        return reverse('preprints:search')

    def test_no_user_permissions_raises_error(self, url, user, view):
        request = RequestFactory().get(url)
        request.user = user
        with pytest.raises(PermissionDenied):
            view.as_view()(request)

    def test_correct_view_permissions(self, url, user, view):

        view_permission = Permission.objects.get(codename='view_preprintservice')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(url)
        request.user = user

        response = view.as_view()(request)
        assert response.status_code == 200

@pytest.mark.urls('admin.base.urls')
class TestPreprintReindex:

    @mock.patch('website.preprints.tasks.send_share_preprint_data')
    @mock.patch('website.settings.SHARE_URL', 'ima_real_website')
    def test_reindex_preprint_share(self, mock_reindex_preprint, preprint, req):
        preprint.provider.access_token = 'totally real access token I bought from a guy wearing a trenchcoat in the summer'
        preprint.provider.save()

        count = AdminLogEntry.objects.count()
        view = views.PreprintReindexShare()
        view = setup_log_view(view, req, guid=preprint._id)
        view.delete(req)

        assert mock_reindex_preprint.called
        assert AdminLogEntry.objects.count() == count + 1

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

    def test_can_approve_withdrawal_request(self, withdrawal_request, submitter, preprint, admin):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value
        original_comment = withdrawal_request.comment

        request = RequestFactory().post(reverse('preprints:approve-withdrawal', kwargs={'guid': preprint._id}))
        request.user = admin

        response = views.PreprintApproveWithdrawalRequest.as_view()(request, guid=preprint._id)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()
        assert withdrawal_request.machine_state == DefaultStates.ACCEPTED.value
        assert original_comment == withdrawal_request.target.withdrawal_justification

    def test_can_reject_withdrawal_request(self, withdrawal_request, admin, preprint):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value

        request = RequestFactory().post(reverse('preprints:reject-withdrawal', kwargs={'guid': preprint._id}))
        request.user = admin

        response = views.PreprintRejectWithdrawalRequest.as_view()(request, guid=preprint._id)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()
        assert withdrawal_request.machine_state == DefaultStates.REJECTED.value
        assert not withdrawal_request.target.withdrawal_justification

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

    @pytest.mark.parametrize('intent, final_state', [
        ('approveRequest', DefaultStates.ACCEPTED.value),
        ('rejectRequest', DefaultStates.REJECTED.value)])
    def test_approve_reject_on_list_view(self, withdrawal_request, admin, intent, final_state):
        assert withdrawal_request.machine_state == DefaultStates.PENDING.value
        original_comment = withdrawal_request.comment
        request = RequestFactory().post(reverse('preprints:withdrawal-requests'), {intent: 'foo', '{}'.format(withdrawal_request._id): 'bar'})
        request.user = admin

        response = views.PreprintWithdrawalRequestList.as_view()(request)
        assert response.status_code == 302

        withdrawal_request.refresh_from_db()
        withdrawal_request.target.refresh_from_db()

        withdrawal_request.machine_state == final_state

        if intent == 'approveRequest':
            assert original_comment == withdrawal_request.target.withdrawal_justification
        else:
            assert not withdrawal_request.target.withdrawal_justification
