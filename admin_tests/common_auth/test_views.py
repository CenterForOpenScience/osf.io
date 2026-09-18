from unittest import mock
import pytest

from django.utils import timezone
from django.test import RequestFactory
from django.http import Http404
from admin.nodes.views import NodeSearchView
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory

from admin_tests.utilities import setup_view, setup_form_view

from osf.models.user import OSFUser
from addons.twofactor.models import UserSettings as TwoFactorUserSettings
from admin.common_auth.views import RegisterUser, LoginView
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

        # email and password are used to authenticate user again
        # on two factor auth, thus are hidden from user to be sure
        # the same user completes two-factor auth and get user object
        # within two different requests: sign in and code submit
        for field in ['email', 'password', 'code']:
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
        view.extra_context = {'form': TwoFactorForm({'code': 'nonono', 'email': self.user.username, 'password': '1234'})}
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
        view.extra_context = {'form': TwoFactorForm({'code': 'yesyes', 'email': self.user.username, 'password': '1234'})}
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
