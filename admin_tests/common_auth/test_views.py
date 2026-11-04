from unittest import mock
import pytest

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.test import RequestFactory
from django.http import Http404
from admin.nodes.views import NodeSearchView
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory

from admin_tests.utilities import setup_view, setup_form_view

from osf.models.user import OSFUser
from addons.twofactor.models import UserSettings as TwoFactorUserSettings
from admin.common_auth.views import RegisterUser, LoginView, AdminUserAudit, AdminUserStaffChange, AdminUserSuperuserRevoke
from admin.common_auth.forms import TwoFactorForm, UserRegistrationForm
from django.contrib.messages.storage.fallback import FallbackStorage


def patch_messages(request):
    # django.contrib.messages has a bug which effects unittests
    # more info here -> https://code.djangoproject.com/ticket/17971
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)


class TestRegisterUser(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.data = {
            'osf_id': 'abc12',
        }
        self.view = RegisterUser()
        self.request = RequestFactory().post('fake_path')

    def test_osf_id_invalid(self):
        form = UserRegistrationForm(data=self.data)
        assert form.is_valid()
        view = setup_form_view(self.view, self.request, form)
        with pytest.raises(Http404):
            view.form_valid(form)

    @mock.patch('admin.common_auth.views.messages.success')
    def test_add_user(self, mock_save):
        count = OSFUser.objects.count()
        self.data.update(osf_id=self.user._id)
        form = UserRegistrationForm(data=self.data)
        assert form.is_valid()
        view = setup_form_view(self.view, self.request, form)
        view.form_valid(form)
        assert mock_save.called
        assert OSFUser.objects.count() == count + 1

    @mock.patch('admin.common_auth.views.messages.success')
    def test_add_user_to_groups(self, mock_success):
        metrics_only, osf_admin, read_only = (
            Group.objects.get(name=name) for name in ('metrics_only', 'osf_admin', 'read_only')
        )
        self.user.groups.add(metrics_only)
        form = UserRegistrationForm(data={'osf_id': self.user._id, 'group_perms': [osf_admin.id, read_only.id]})
        assert form.is_valid()
        view = setup_form_view(self.view, self.request, form)
        view.form_valid(form)

        self.user.refresh_from_db()
        assert self.user.is_staff
        assert set(self.user.groups.all()) == {metrics_only, osf_admin, read_only}

    def get_register_page(self, user):
        request = RequestFactory().get('/fake_path')
        request.user = user
        return RegisterUser.as_view()(request)

    def test_register_page_requires_admin_user_management_permission(self):
        with pytest.raises(PermissionDenied):
            self.get_register_page(AuthUserFactory(is_staff=True))

        manager = AuthUserFactory(is_staff=True)
        manager.groups.add(Group.objects.get(name='admin_user_management'))
        assert self.get_register_page(manager).status_code == 200


@pytest.fixture()
def manager():
    user = AuthUserFactory(is_staff=True)
    user.groups.add(Group.objects.get(name='admin_user_management'))
    return user


def post_audit_change(view_class, user, guid, data=None):
    request = RequestFactory().post('/fake_path', data or {})
    request.user = user
    patch_messages(request)
    return view_class.as_view()(request, guid=guid)


@pytest.mark.django_db
@pytest.mark.urls('admin.base.urls')
class TestAdminUserAudit:

    def get_audit_page(self, user, **params):
        request = RequestFactory().get('/fake_path', params)
        request.user = user
        return AdminUserAudit.as_view()(request)

    def test_lists_staff_users_and_superusers(self, manager):
        staff = AuthUserFactory(is_staff=True)
        superuser = AuthUserFactory(is_superuser=True)
        regular_user = AuthUserFactory()

        admin_users = list(self.get_audit_page(manager).context_data['admin_users'])

        assert {manager, staff, superuser} <= set(admin_users)
        assert regular_user not in admin_users
        assert admin_users.index(superuser) < admin_users.index(staff)

    def test_lists_admin_app_groups_only(self, manager):
        staff = AuthUserFactory(is_staff=True)
        osf_admin = Group.objects.get(name='osf_admin')
        staff.groups.add(osf_admin)
        ProjectFactory(creator=staff)
        assert staff.groups.filter(name__startswith='node_').exists()

        admin_users = self.get_audit_page(manager).context_data['admin_users']

        listed_staff = next(admin_user for admin_user in admin_users if admin_user == staff)
        assert listed_staff.guid == staff._id
        assert listed_staff.admin_app_groups == [osf_admin]

    def test_page_out_of_range_shows_last_page(self, manager):
        page = self.get_audit_page(manager, page=1000).context_data['page']
        assert page.number == page.paginator.num_pages

    def test_requires_admin_user_management_permission(self):
        with pytest.raises(PermissionDenied):
            self.get_audit_page(AuthUserFactory(is_staff=True))


@pytest.mark.django_db
@pytest.mark.urls('admin.base.urls')
class TestAdminUserStaffChange:

    def test_revoke_staff_status(self, manager):
        staff = AuthUserFactory(is_staff=True)

        response = post_audit_change(AdminUserStaffChange, manager, staff._id, {'is_staff': 'false', 'page': '2'})

        assert response.status_code == 302
        assert response.url == '/account/audit/?page=2'
        staff.refresh_from_db()
        assert not staff.is_staff

    def test_grant_staff_status(self, manager):
        superuser = AuthUserFactory(is_superuser=True)

        response = post_audit_change(AdminUserStaffChange, manager, superuser._id, {'is_staff': 'true'})

        assert response.url == '/account/audit/'
        superuser.refresh_from_db()
        assert superuser.is_staff

    def test_cannot_change_own_staff_status(self, manager):
        post_audit_change(AdminUserStaffChange, manager, manager._id, {'is_staff': 'false'})

        manager.refresh_from_db()
        assert manager.is_staff

    def test_requires_admin_user_management_permission(self):
        staff = AuthUserFactory(is_staff=True)

        with pytest.raises(PermissionDenied):
            post_audit_change(AdminUserStaffChange, AuthUserFactory(is_staff=True), staff._id, {'is_staff': 'false'})

        staff.refresh_from_db()
        assert staff.is_staff


@pytest.mark.django_db
@pytest.mark.urls('admin.base.urls')
class TestAdminUserSuperuserRevoke:

    def test_revoke_superuser_status(self, manager):
        superuser = AuthUserFactory(is_staff=True, is_superuser=True)
        response = post_audit_change(AdminUserSuperuserRevoke, manager, superuser._id, {'page': '1'})

        assert response.url == '/account/audit/?page=1'
        superuser.refresh_from_db()
        assert not superuser.is_superuser
        assert superuser.is_staff

    def test_does_not_grant_superuser_status(self, manager):
        staff = AuthUserFactory(is_staff=True)
        post_audit_change(AdminUserSuperuserRevoke, manager, staff._id)

        staff.refresh_from_db()
        assert not staff.is_superuser

    def test_requires_admin_user_management_permission(self):
        superuser = AuthUserFactory(is_staff=True, is_superuser=True)

        with pytest.raises(PermissionDenied):
            post_audit_change(AdminUserSuperuserRevoke, AuthUserFactory(is_staff=True), superuser._id)

        superuser.refresh_from_db()
        assert superuser.is_superuser


class TestLoginView(AdminTestCase):

    def setUp(self):
        self.view = LoginView()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.user.set_password('1234')
        self.user.save()

    def create_user_two_factor_settings(self):
        return TwoFactorUserSettings.objects.create(owner=self.user)

    def test_login_form_displayed_on_initial_get_request(self):
        request = RequestFactory().get('/fake_path')
        view = setup_view(self.view, request)
        response = view.get(request)
        assert response.template_name == ['login.html']
        assert not hasattr(request, 'user')

    def test_login_post_invalid_credentials(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': 'invalid'})
        patch_messages(request)

        view = setup_view(self.view, request)
        with mock.patch('django.contrib.messages.error') as message_error:
            response = view.post(request)

        assert response.status_code == 302
        assert response.headers['Location'] == '/account/login'
        message_error.assert_called_with(request, 'Email and/or Password incorrect. Please try again.')
        assert not hasattr(request, 'user')

    def test_login_post_correct_credentials_disabled_two_factor_auth(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        patch_messages(request)

        view = setup_view(self.view, request)
        with mock.patch('django.contrib.messages.error') as message_error:
            response = view.post(request)

        # redirect to the same page for two-factor
        assert response.headers['Location'] == '/account/login'
        assert response.status_code == 302
        message_error.assert_called_with(request, 'Two-factor authentication must be enabled.')
        assert not hasattr(request, 'user')

    def test_login_post_deleted_two_factor(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        settings = self.create_user_two_factor_settings()
        settings.is_confirmed = True
        settings.deleted = timezone.now()
        settings.save()

        patch_messages(request)

        view = setup_view(self.view, request)
        with mock.patch('django.contrib.messages.error') as message_error:
            response = view.post(request)

        # redirect to the same page for two-factor
        assert response.headers['Location'] == '/account/login'
        assert response.status_code == 302
        message_error.assert_called_with(request, 'Two-factor authentication must be enabled.')
        assert not hasattr(request, 'user')

    def test_login_post_unconfirmed_two_factor(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        settings = self.create_user_two_factor_settings()
        settings.is_confirmed = False
        settings.deleted = None
        settings.save()

        patch_messages(request)

        view = setup_view(self.view, request)
        with mock.patch('django.contrib.messages.error') as message_error:
            response = view.post(request)

        # redirect to the same page for two-factor
        assert response.headers['Location'] == '/account/login'
        assert response.status_code == 302
        message_error.assert_called_with(request, 'Two-factor authentication must be enabled.')
        assert not hasattr(request, 'user')

    def test_login_post_set_confirmed_two_factor(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        settings = self.create_user_two_factor_settings()
        settings.is_confirmed = True
        settings.deleted = None
        settings.save()

        patch_messages(request)

        view = setup_view(self.view, request)
        with mock.patch('django.contrib.messages.error') as message_error:
            with mock.patch('admin.common_auth.views.render') as mock_render:
                view.post(request)

        message_error.assert_not_called()
        assert 'two_factor.html' in mock_render.call_args[0]

        # user guid is used to authenticate user again
        # on two factor auth, thus we hide it from the form to be sure
        # the same user completes two-factor auth and get user object
        # within two different requests: sign in and code submit
        for field in ['guid', 'code']:
            assert field in mock_render.call_args[0][2]['form'].fields

        assert not hasattr(request, 'user')

    def test_login_post_invalid_code(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        settings = self.create_user_two_factor_settings()
        settings.is_confirmed = True
        settings.deleted = None
        settings.save()

        patch_messages(request)

        view = setup_view(self.view, request)
        # imitate case when email and password are valid and enter an invalid code
        view.extra_context = {'form': TwoFactorForm({'code': 'nonono', 'guid': self.user._id})}
        with mock.patch('django.contrib.messages.error') as message_error:
            with mock.patch('admin.common_auth.views.render') as _:
                with mock.patch('addons.twofactor.models.UserSettings.verify_code') as mock_verify_code:
                    mock_verify_code.return_value = False
                    view.post(request)

        message_error.assert_called_with(request, 'Invalid two-factor code. Please try again.')
        assert not hasattr(request, 'user')

    def test_login_post_valid_code(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        settings = self.create_user_two_factor_settings()
        settings.is_confirmed = True
        settings.deleted = None
        settings.save()

        patch_messages(request)

        def custom_login(request, user, *args, **kwargs):
            request.user = user

        view = setup_view(self.view, request)
        # imitate case when email and password are valid and enter a valid code
        view.extra_context = {'form': TwoFactorForm({'code': 'yesyes', 'guid': str(self.user._id)})}
        with mock.patch('django.contrib.messages.error') as message_error:
            with mock.patch('admin.common_auth.views.render') as mock_render:
                with mock.patch('addons.twofactor.models.UserSettings.verify_code') as mock_verify_code:
                    with mock.patch('admin.common_auth.views.login') as mocked_login:
                        mocked_login.side_effect = custom_login
                        mock_verify_code.return_value = True
                        view.post(request)

        message_error.assert_not_called()
        mock_render.assert_not_called()
        mocked_login.assert_called_once_with(request, self.user)
        # user is assigned to request only after successfull log in and verification code via login()
        assert hasattr(request, 'user')

        response = NodeSearchView.as_view()(request)
        assert response.status_code == 200

    def test_two_factor_without_guid_redirects_to_login(self):
        request = RequestFactory().post('/fake_path', data={'email': self.user.username, 'password': '1234'})
        settings = self.create_user_two_factor_settings()
        settings.is_confirmed = True
        settings.deleted = None
        settings.save()

        patch_messages(request)

        def custom_login(request, user, *args, **kwargs):
            request.user = user

        view = setup_view(self.view, request)
        view.extra_context = {'form': TwoFactorForm({'code': 'yesyes'})}
        with mock.patch('django.contrib.messages.error') as message_error:
            with mock.patch('admin.common_auth.views.redirect') as mock_redirect:
                with mock.patch('addons.twofactor.models.UserSettings.verify_code') as mock_verify_code:
                    with mock.patch('admin.common_auth.views.login') as mocked_login:
                        mocked_login.side_effect = custom_login
                        mock_verify_code.return_value = True
                        view.post(request)

        message_error.assert_called_with(request, 'Email and/or Password incorrect. Please try again.')
        mock_redirect.assert_called()
        mocked_login.assert_not_called()
        assert not hasattr(request, 'user')
