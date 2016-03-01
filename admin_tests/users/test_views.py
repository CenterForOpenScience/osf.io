from django.test import RequestFactory
from nose.tools import *  # flake8: noqa
import mock

from tests.base import AdminTestCase
from tests.factories import UserFactory, AuthUserFactory
from admin_tests.utilities import setup_view

from admin.users.views import UserView, remove_2_factor


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

    @mock.patch('admin.users.views.User.delete_addon')
    def test_remove_two_factor_get(self, mock_delete_addon):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        remove_2_factor(request, guid)
        assert_equal(mock_delete_addon.call_args_list, [])

    @mock.patch('admin.users.views.User.delete_addon')
    def test_remove_two_factor_post(self, mock_delete_addon):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().post('/fake_path')
        remove_2_factor(request, guid)
        mock_delete_addon.assert_called_with('twofactor')

    @mock.patch('admin.users.views.User.delete_addon')
    def test_remove_two_factor_delete(self, mock_delete_addon):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().delete('/fake_path')
        remove_2_factor(request, guid)
        mock_delete_addon.assert_called_with('twofactor')

    def test_integration_delete_two_factor(self):
        user = AuthUserFactory()
        guid = user._id
        user_addon = user.get_or_add_addon('twofactor')
        assert_not_equal(user_addon, None)
        user_settings = user.get_addon('twofactor')
        assert_not_equal(user_settings, None)
        request = RequestFactory().post('/fake_path')
        remove_2_factor(request, guid)
        post_addon = user.get_addon('twofactor')
        assert_equal(post_addon, None)
