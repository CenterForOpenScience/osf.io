from django.test import RequestFactory
from nose.tools import *  # flake8: noqa
import mock

from tests.base import AdminTestCase
from tests.factories import UserFactory
from website import settings
from tests.factories import UserFactory, AuthUserFactory
from admin_tests.utilities import setup_view
from admin.users.views import UserView, disable_user, reactivate_user, remove_2_factor


class TestUserView(AdminTestCase):

    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request)
        with assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        assert_is_instance(res, dict)

    def test_name_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        assert_equal(res[UserView.context_object_name], temp_object)


class TestDisableUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().get('/fake_path')

    def test_disable_user(self):
        guid = self.user._id
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        disable_user(self.request, guid)
        assert_true(self.user.is_disabled)

    def test_reactivate_user(self):
        guid = self.user._id
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        disable_user(self.request, guid)
        reactivate_user(self.request, guid)
        assert_false(self.user.is_disabled)


class TestRemove2Factor(AdminTestCase):
    def setUp(self):
        super(TestRemove2Factor, self).setUp()
        self.user = AuthUserFactory()

    @mock.patch('admin.users.views.User.delete_addon')
    def test_remove_two_factor_get(self, mock_delete_addon):
        guid = self.user._id
        request = RequestFactory().get('/fake_path')
        remove_2_factor(request, guid)
        mock_delete_addon.assert_called_with('twofactor')

    def test_integration_delete_two_factor(self):
        guid = self.user._id
        user_addon = self.user.get_or_add_addon('twofactor')
        assert_not_equal(user_addon, None)
        user_settings = self.user.get_addon('twofactor')
        assert_not_equal(user_settings, None)
        request = RequestFactory().post('/fake_path')
        remove_2_factor(request, guid)
        post_addon = self.user.get_addon('twofactor')
        assert_equal(post_addon, None)
