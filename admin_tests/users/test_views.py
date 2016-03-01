from django.test import RequestFactory
from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase
from tests.factories import UserFactory
from admin_tests.utilities import setup_view

from admin.users.views import UserView, ResetPasswordView


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


class TestResetPasswordView(AdminTestCase):
    def test_reset_password_context(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = ResetPasswordView()
        view = setup_view(view, request, guid=guid)
        res = view.get_context_data()
        assert_is_instance(res, dict)
        assert_in((user.emails[0], user.emails[0]), view.initial['emails'])
