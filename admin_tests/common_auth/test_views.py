from unittest import mock
import pytest

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.test import RequestFactory
from django.urls import resolve, reverse
from django.http import Http404, HttpResponse
from admin.nodes.views import NodeSearchView
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory

from admin_tests.utilities import setup_view, setup_form_view

from osf.models.user import OSFUser
from addons.twofactor.models import UserSettings as TwoFactorUserSettings
from admin.common_auth.views import (
    LOGIN_ERROR_MESSAGE,
    RegisterUser,
    LoginView,
    AdminUserAudit,
    AdminUserStaffChange,
    AdminUserSuperuserRevoke,
)
from admin.common_auth.forms import UserRegistrationForm
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
        self.user = AuthUserFactory(is_staff=True, is_superuser=True)
        self.user.set_password('1234')
        self.user.save()

    def enable_two_factor(self, user=None, is_confirmed=True, deleted=None):
        return TwoFactorUserSettings.objects.create(owner=user or self.user, is_confirmed=is_confirmed, deleted=deleted)

    def post_login(self, data, valid_code=True):
        """Post to the login view. Returns the response, the request and the mocks of messages.error and login"""
        request = RequestFactory().post('/fake_path', data=data)
        request._dont_enforce_csrf_checks = True
        patch_messages(request)

        def custom_login(request, user, *args, **kwargs):
            request.user = user

        view = setup_view(self.view, request)
        with mock.patch('django.contrib.messages.error') as message_error:
            with mock.patch('addons.twofactor.models.UserSettings.verify_code', return_value=valid_code):
                with mock.patch('admin.common_auth.views.login', side_effect=custom_login) as mocked_login:
                    response = view.dispatch(request)
        return response, request, message_error, mocked_login

    def assert_login_failed(self, data, valid_code=True):
        response, request, message_error, mocked_login = self.post_login(data, valid_code=valid_code)

        # every failure looks the same, whichever check of whichever step failed
        assert response.status_code == 302
        assert response.headers['Location'] == '/account/login'
        message_error.assert_called_once_with(request, LOGIN_ERROR_MESSAGE)
        mocked_login.assert_not_called()
        assert not hasattr(request, 'user')

    def password_data(self, password='1234'):
        return {'email': self.user.username, 'password': password}

    def two_factor_data(self, **overrides):
        data = {'guid': self.user._id, 'admin_login_id': self.user.admin_login_id, 'code': '123456'}
        data.update(overrides)
        return {key: value for key, value in data.items() if value is not None}

    def test_login_form_displayed_on_initial_get_request(self):
        request = RequestFactory().get('/fake_path')
        view = setup_view(self.view, request)
        response = view.get(request)
        assert response.template_name == ['login.html']
        assert not hasattr(request, 'user')

    def test_login_post_invalid_credentials(self):
        self.enable_two_factor()
        self.assert_login_failed(self.password_data(password='invalid'))

    def test_login_post_correct_credentials_disabled_two_factor_auth(self):
        self.assert_login_failed(self.password_data())

    def test_login_post_deleted_two_factor(self):
        self.enable_two_factor(deleted=timezone.now())
        self.assert_login_failed(self.password_data())

    def test_login_post_unconfirmed_two_factor(self):
        self.enable_two_factor(is_confirmed=False)
        self.assert_login_failed(self.password_data())

    def test_login_post_not_staff(self):
        self.enable_two_factor()
        self.user.is_staff = False
        self.user.is_superuser = True
        self.user.save()
        self.assert_login_failed(self.password_data())

    def test_login_post_correct_credentials_displays_two_factor_form(self):
        self.enable_two_factor()

        with mock.patch('admin.common_auth.views.render', return_value=HttpResponse()) as mock_render:
            _, request, message_error, mocked_login = self.post_login(self.password_data())

        message_error.assert_not_called()
        mocked_login.assert_not_called()
        assert not hasattr(request, 'user')
        assert 'two_factor.html' in mock_render.call_args[0]

        # the two-factor step is a separate request: the hidden guid tells it which user is logging in
        # and the hidden admin_login_id proves that this user has passed the password step
        form = mock_render.call_args[0][2]['form']
        assert form.initial['guid'] == self.user._id
        assert self.user.check_admin_login_id(form.initial['admin_login_id'])
        rendered_form = form.as_p()
        for field in ('guid', 'admin_login_id'):
            assert f'type="hidden" name="{field}" value="{form.initial[field]}"' in rendered_form

    def test_two_factor_post_valid_code(self):
        self.enable_two_factor()

        response, request, message_error, mocked_login = self.post_login(self.two_factor_data())

        message_error.assert_not_called()
        mocked_login.assert_called_once_with(request, self.user)
        assert response.status_code == 302
        assert response.headers['Location'] == reverse('home')

        # the logged-in user can use the admin app
        admin_request = RequestFactory().get('/fake_path')
        admin_request.user = request.user
        assert NodeSearchView.as_view()(admin_request).status_code == 200

    def test_two_factor_post_invalid_code(self):
        self.enable_two_factor()
        self.assert_login_failed(self.two_factor_data(), valid_code=False)

    def test_two_factor_post_without_admin_login_id(self):
        # a guid and a valid code are not enough: the password step can't be skipped
        self.enable_two_factor()
        self.assert_login_failed(self.two_factor_data(admin_login_id=None))

    def test_two_factor_post_without_guid(self):
        self.enable_two_factor()
        self.assert_login_failed(self.two_factor_data(guid=None))

    def test_two_factor_post_unknown_guid(self):
        self.enable_two_factor()
        self.assert_login_failed(self.two_factor_data(guid='abc12'))

    def test_two_factor_post_forged_admin_login_id(self):
        self.enable_two_factor()
        self.assert_login_failed(self.two_factor_data(admin_login_id='forged'))
        self.assert_login_failed(self.two_factor_data(admin_login_id=f'{self.user._id}:{self.user.pk}'))

    def test_two_factor_post_admin_login_id_of_another_user(self):
        self.enable_two_factor()
        other_staff = AuthUserFactory(is_staff=True)
        self.assert_login_failed(self.two_factor_data(admin_login_id=other_staff.admin_login_id))

    def test_two_factor_post_not_staff_anymore(self):
        self.enable_two_factor()
        data = self.two_factor_data()
        self.user.is_staff = False
        self.user.save()
        self.assert_login_failed(data)

    def test_two_factor_post_disabled_user(self):
        self.enable_two_factor()
        data = self.two_factor_data()
        self.user.is_disabled = True
        self.user.save()
        assert not self.user.is_active
        self.assert_login_failed(data)

    def test_two_factor_post_disabled_two_factor_auth(self):
        self.assert_login_failed(self.two_factor_data())

    def test_django_admin_login_uses_login_view(self):
        match = resolve(reverse('admin:login'))
        assert match.func.view_class is LoginView
