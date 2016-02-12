from django.test import RequestFactory
from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase
from tests.factories import NodeFactory
from admin_tests.utilities import setup_view

from admin.nodes.views import NodeView


class TestNodeView(AdminTestCase):

    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request)
        with assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        node = NodeFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        assert_is_instance(res, dict)

    def test_name_data(self):
        node = NodeFactory()
        guid = node._id
        request = RequestFactory().get('/fake_path')
        view = NodeView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        assert_equal(res[NodeView.context_object_name], temp_object)
