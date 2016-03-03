from django.test import RequestFactory
from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase
from tests.factories import UserFactory
from admin_tests.utilities import setup_view

from admin.users.views import UserFormView
from admin.base.forms import GuidForm


class TestUserFormView(AdminTestCase):

    def test_context_data_not_existing_guid(self):
        guid = '12345'
        request = RequestFactory().get('/fake-path/?guid={}'.format(guid))
        view = UserFormView()
        view = setup_view(view, request)
        with assert_raises(AttributeError):
            view.get_context_data()

    def test_context_data_no_guid(self):
        request = RequestFactory().get('/fake-path')
        view = UserFormView()
        view = setup_view(view, request)
        res = view.get_context_data()
        assert_is_instance(res['form'], GuidForm)
        assert_is_instance(res['view'], UserFormView)
        assert_is_none(res['guid_object'])

    def test_context_data_load(self):
        node = UserFactory()
        guid = node._id
        request = RequestFactory().get('/fake-path/?guid={}'.format(guid))
        view = UserFormView()
        view = setup_view(view, request)
        res = view.get_context_data()
        assert_is_instance(res['form'], GuidForm)
        assert_is_instance(res['view'], UserFormView)
        assert_is_instance(res['guid_object'], dict)

    def test_success_url_implemented(self):
        node = UserFactory()
        guid = node._id
        request = RequestFactory().get('/fake-path/?guid={}'.format(guid))
        view = UserFormView()
        view = setup_view(view, request)
        view.get_context_data()
        assert_equal(view.success_url, u'/admin/users/?guid={}'.format(guid))
