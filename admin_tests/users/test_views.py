from django.test import RequestFactory
from nose import tools as nt
import mock

from tests.base import AdminTestCase
from website import settings
from framework.auth import User
from tests.factories import UserFactory, AuthUserFactory
from admin_tests.utilities import setup_view, setup_log_view

from admin.users.views import (
    UserView,
    ResetPasswordView,
    User2FactorDeleteView,
    UserDeleteView,
)
from admin.common_auth.logs import OSFLogEntry


class TestUserView(AdminTestCase):
    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request)
        with nt.assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        nt.assert_is_instance(res, dict)

    def test_name_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        nt.assert_equal(res[UserView.context_object_name], temp_object)


class TestResetPasswordView(AdminTestCase):
    def test_reset_password_context(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = ResetPasswordView()
        view = setup_view(view, request, guid=guid)
        res = view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in((user.emails[0], user.emails[0]), view.initial['emails'])


class TestDisableUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = UserDeleteView()
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, User)

    def test_get_context(self):
        res = self.view.get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        self.user.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)

    def test_reactivate_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        self.view.delete(self.request)
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        self.user.reload()
        nt.assert_false(self.user.is_disabled)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)


class TestRemove2Factor(AdminTestCase):
    def setUp(self):
        super(TestRemove2Factor, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = User2FactorDeleteView()
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    @mock.patch('admin.users.views.User.delete_addon')
    def test_remove_two_factor_get(self, mock_delete_addon):
        self.view.delete(self.request)
        mock_delete_addon.assert_called_with('twofactor')

    def test_integration_delete_two_factor(self):
        user_addon = self.user.get_or_add_addon('twofactor')
        nt.assert_not_equal(user_addon, None)
        user_settings = self.user.get_addon('twofactor')
        nt.assert_not_equal(user_settings, None)
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        post_addon = self.user.get_addon('twofactor')
        nt.assert_equal(post_addon, None)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)
