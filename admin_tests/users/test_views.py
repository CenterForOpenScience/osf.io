from unittest import mock
from furl import furl
import pytz
import pytest
from datetime import datetime, timedelta

from django.test import RequestFactory
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage

from tests.base import AdminTestCase
from website import settings
from framework.auth import Auth
from osf.models.user import OSFUser
from osf.models.spam import SpamStatus
from osf_tests.factories import (
    UserFactory,
    AuthUserFactory,
    ProjectFactory,
    UnconfirmedUserFactory
)
from admin_tests.utilities import setup_view, setup_log_view, setup_form_view

from admin.users import views
from admin.users.forms import UserSearchForm, MergeUserForm
from osf.models.admin_log_entry import AdminLogEntry

pytestmark = pytest.mark.django_db


def patch_messages(request):
    # django.contrib.messages has a bug which effects unittests
    # more info here -> https://code.djangoproject.com/ticket/17971
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)


class TestUserView(AdminTestCase):

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:user', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            views.UserView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('users:user', kwargs={'guid': guid}))
        request.user = user

        response = views.UserView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestResetPasswordView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.request.POST = {'emails': self.user.emails.all()}
        self.request.user = self.user

        self.plain_view = views.ResetPasswordView
        self.view = setup_view(self.plain_view(), self.request, guid=self.user._id)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()

        guid = user._id
        request = RequestFactory().post(reverse('users:reset-password', kwargs={'guid': guid}))
        request.POST = {'emails': user.emails.all()}

        request.user = user

        with self.assertRaises(PermissionDenied):
            views.ResetPasswordView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(reverse('users:reset-password', kwargs={'guid': guid}))
        request.POST = {'emails': ', '.join(user.emails.all().values_list('address', flat=True))}
        request.user = user

        response = views.ResetPasswordView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 302)


class TestGDPRDeleteUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.UserGDPRDeleteView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_gdpr_delete_user(self):
        patch_messages(self.request)

        count = AdminLogEntry.objects.count()
        self.view().post(self.request)
        self.user.reload()
        assert self.user.deleted
        assert AdminLogEntry.objects.count() == count + 1

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:GDPR-delete', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(reverse('users:GDPR-delete', kwargs={'guid': user._id}))
        patch_messages(request)
        request.user = user

        response = self.view.as_view()(request, guid=user._id)
        self.assertEqual(response.status_code, 302)


class TestDisableUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.UserDisableView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_disable_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = AdminLogEntry.objects.count()
        self.view().post(self.request)
        self.user.reload()
        assert self.user.is_disabled
        assert AdminLogEntry.objects.count() == count + 1

    def test_reactivate_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        self.view().post(self.request)
        count = AdminLogEntry.objects.count()
        self.view().post(self.request)
        self.user.reload()
        assert not self.user.is_disabled
        assert not self.user.requested_deactivation
        assert AdminLogEntry.objects.count() == count + 1

    def test_no_user(self):
        view = setup_view(views.UserDisableView(), self.request, guid='meh')
        with pytest.raises(OSFUser.DoesNotExist):
            view.post(self.request)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:disable', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(reverse('users:disable', kwargs={'guid': guid}))
        request.user = user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 302)


class TestHamUserRestore(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.UserConfirmHamView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_enable_user(self):
        self.user.is_disabled = True
        self.user.save()
        assert self.user.is_disabled
        self.view().post(self.request)
        self.user.reload()

        assert not self.user.is_disabled
        assert self.user.spam_status == SpamStatus.HAM


class TestDisableSpamUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.public_node = ProjectFactory(creator=self.user, is_public=True)
        self.private_node = ProjectFactory(creator=self.user, is_public=False)
        self.request = RequestFactory().post('/fake_path')
        self.view = views.UserConfirmSpamView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_disable_spam_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        self.view().post(self.request)
        self.user.reload()
        self.public_node.reload()
        assert self.user.is_disabled
        assert self.user.spam_status == SpamStatus.SPAM
        assert not self.public_node.is_public
        assert AdminLogEntry.objects.exists()

    def test_no_user(self):
        view = setup_view(self.view(), self.request, guid='meh')
        with pytest.raises(OSFUser.DoesNotExist):
            view.post(self.request)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().post(reverse('users:confirm-spam', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(reverse('users:confirm-spam', kwargs={'guid': guid}))
        request.user = user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 302)


class SpamUserListMixin:
    def setUp(self):

        self.flagged_user = UserFactory()
        self.flagged_user.spam_status = SpamStatus.FLAGGED
        self.flagged_user.save()

        self.spam_user = UserFactory()
        self.spam_user.spam_status = SpamStatus.SPAM
        self.spam_user.save()

        self.ham_user = UserFactory()
        self.ham_user.spam_status = SpamStatus.HAM
        self.ham_user.save()

        self.request = RequestFactory().post('/fake_path')

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(self.url)
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.plain_view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        spam_permission = Permission.objects.get(codename='view_spam')
        user.user_permissions.add(view_permission)
        user.user_permissions.add(spam_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestFlaggedSpamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super().setUp()
        self.plain_view = views.UserFlaggedSpamList
        self.view = setup_log_view(self.plain_view(), self.request)
        self.url = reverse('users:flagged-spam')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        assert qs.count() == 1
        assert qs[0]._id == self.flagged_user._id


class TestConfirmedSpamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super().setUp()
        self.plain_view = views.UserKnownSpamList
        self.view = setup_log_view(self.plain_view(), self.request)

        self.url = reverse('users:known-spam')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        assert qs.count() == 1
        assert qs[0]._id == self.spam_user._id


class TestConfirmedHamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super().setUp()
        self.plain_view = views.UserKnownHamList
        self.view = setup_log_view(self.plain_view(), self.request)

        self.url = reverse('users:known-ham')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        assert qs.count() == 1
        assert qs[0]._id == self.ham_user._id


class TestRemove2Factor(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.User2FactorDeleteView
        self.setup_view = setup_log_view(self.view(), self.request, guid=self.user._id)

        self.url = reverse('users:remove2factor', kwargs={'guid': self.user._id})

    def test_integration_delete_two_factor(self):
        user_addon = self.user.get_or_add_addon('twofactor')
        assert user_addon is not None
        user_settings = self.user.get_addon('twofactor')
        assert user_settings is not None
        count = AdminLogEntry.objects.count()
        self.setup_view.post(self.request)
        post_addon = self.user.get_addon('twofactor')
        assert post_addon is None
        assert AdminLogEntry.objects.count() == count + 1

    def test_no_user_permissions_raises_error(self):
        guid = self.user._id
        request = RequestFactory().post(self.url)
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        guid = self.user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        self.user.user_permissions.add(change_permission)
        self.user.save()

        request = RequestFactory().post(self.url)
        request.user = self.user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 302)


class TestUserSearchView(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user_2 = AuthUserFactory(fullname='Jeff Hardy')
        self.user_3 = AuthUserFactory(fullname='Reby Sky')
        self.user_4 = AuthUserFactory(fullname='King Maxel Hardy')

        self.user_2_alternate_email = 'brothernero@delapidatedboat.com'
        self.user_2.emails.create(address=self.user_2_alternate_email)
        self.user_2.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.UserSearchView()
        self.view = setup_form_view(self.view, self.request, form=UserSearchForm())

    def test_search_user_by_guid(self):
        form_data = {
            'guid': self.user_1.guids.first()._id
        }
        form = UserSearchForm(data=form_data)
        assert form.is_valid()
        response = self.view.form_valid(form)
        assert response.status_code == 302
        assert response.headers['location'] == f'/users/{self.user_1.guids.first()._id}/'

    def test_search_user_by_name(self):
        form_data = {
            'name': 'Hardy'
        }
        form = UserSearchForm(data=form_data)
        assert form.is_valid()
        response = self.view.form_valid(form)
        assert response.status_code == 302
        assert response.headers['location'] == '/users/search/Hardy/'

    def test_search_user_by_name_with_punctuation(self):
        form_data = {
            'name': 'Dr. Sportello-Fay, PI @, #, $, %, ^, &, *, (, ), ~'
        }
        form = UserSearchForm(data=form_data)
        assert form.is_valid()
        response = self.view.form_valid(form)
        assert response.status_code == 302
        assert response.headers['location'] == '/users/search/Dr.%20Sportello-Fay,%20PI%20@,%20%23,%20$,%20%25,%20%5E,%20&,%20*,%20(,%20),%20~/'

    def test_search_user_by_username(self):
        form_data = {
            'email': self.user_1.username
        }
        form = UserSearchForm(data=form_data)
        assert form.is_valid()
        response = self.view.form_valid(form)
        assert response.status_code == 302
        assert response.headers['location'] == f'/users/{self.user_1.guids.first()._id}/'

    def test_search_user_by_alternate_email(self):
        form_data = {
            'email': self.user_2_alternate_email
        }
        form = UserSearchForm(data=form_data)
        assert form.is_valid()
        response = self.view.form_valid(form)
        assert response.status_code == 302
        assert response.headers['location'] == f'/users/{self.user_2.guids.first()._id}/'

    def test_search_user_list(self):
        view = views.UserSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'Hardy'}

        results = view.get_queryset()

        assert len(results) == 3
        for user in results:
            assert 'Hardy' in user.fullname

    def test_search_user_list_case_insensitive(self):
        view = views.UserSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'hardy'}

        results = view.get_queryset()

        assert len(results) == 3
        for user in results:
            assert 'Hardy' in user.fullname


class TestGetLinkView(AdminTestCase):

    def test_get_user_confirmation_link(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetUserConfirmationLink()
        view = setup_view(view, request, guid=user._id)

        user_token = list(user.email_verifications.keys())[0]
        ideal_link_path = f'/confirm/{user._id}/{user_token}/'
        link = view.get_link(user)
        link_path = str(furl(link).path)

        assert link_path == ideal_link_path

    def test_get_user_confirmation_link_with_expired_token(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetUserConfirmationLink()
        view = setup_view(view, request, guid=user._id)

        old_user_token = list(user.email_verifications.keys())[0]
        user.email_verifications[old_user_token]['expiration'] = datetime.utcnow().replace(tzinfo=pytz.utc) - timedelta(hours=24)
        user.save()

        link = view.get_link(user)
        new_user_token = list(user.email_verifications.keys())[0]

        link_path = str(furl(link).path)
        ideal_link_path = f'/confirm/{user._id}/{new_user_token}/'

        assert link_path == ideal_link_path

    def test_get_password_reset_link(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetPasswordResetLink()
        view = setup_view(view, request, guid=user._id)

        link = view.get_link(user)

        user_token = user.verification_key_v2.get('token')
        assert user_token is not None

        ideal_link_path = f'/resetpassword/{user._id}/{user_token}'
        link_path = str(furl(link).path)

        assert link_path == ideal_link_path

    def test_get_unclaimed_node_links(self):
        project = ProjectFactory()
        unregistered_contributor = project.add_unregistered_contributor(fullname='Brother Nero', email='matt@hardyboyz.biz', auth=Auth(project.creator))
        project.save()

        request = RequestFactory().get('/fake_path')
        view = views.GetUserClaimLinks()
        view = setup_view(view, request, guid=unregistered_contributor._id)

        links = view.get_claim_links(unregistered_contributor)
        unclaimed_records = unregistered_contributor.unclaimed_records

        assert len(links) == 1
        assert len(links) == len(unclaimed_records.keys())
        link = links[0]

        assert project._id in link
        assert unregistered_contributor.unclaimed_records[project._id]['token'] in link


class TestUserReindex(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()

    @mock.patch('website.search.search.update_user')
    def test_reindex_user_elastic(self, mock_reindex_elastic):
        count = AdminLogEntry.objects.count()
        view = views.UserReindexElastic()
        view = setup_log_view(view, self.request, guid=self.user._id)
        view.post(self.request)

        assert mock_reindex_elastic.called
        assert AdminLogEntry.objects.count() == count + 1


class TestUserMerge(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.request = RequestFactory().post('/fake_path')

    @mock.patch('osf.models.user.OSFUser.merge_user')
    def test_merge_user(self, mock_merge_user):
        user = UserFactory()
        user_merged = UserFactory()

        view = views.UserMergeAccounts()
        view = setup_log_view(view, self.request, guid=user._id)

        invalid_form = MergeUserForm(data={'user_guid_to_be_merged': 'Not a valid Guid'})
        valid_form = MergeUserForm(data={'user_guid_to_be_merged': user_merged._id})

        assert not invalid_form.is_valid()
        assert valid_form.is_valid()

        view.form_valid(valid_form)
        mock_merge_user.assert_called_with(user_merged)
