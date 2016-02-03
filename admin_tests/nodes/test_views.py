from django.test import RequestFactory
from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase
from tests.factories import NodeFactory
from admin_tests.utilities import setup_view

from admin.nodes.views import NodeFormView
from admin.nodes.forms import NodeForm


class NodeFormViewTest(AdminTestCase):
    def setUp(self):
        super(NodeFormViewTest, self).setUp()

    def test_context_data_not_existing_guid(self):
        guid = '12345'
        request = RequestFactory().get('/fake-path/?guid={}'.format(guid))
        view = NodeFormView()
        view = setup_view(view, request)
        with assert_raises(AttributeError):
            view.get_context_data()

    def test_context_data_no_guid(self):
        request = RequestFactory().get('/fake-path')
        view = NodeFormView()
        view = setup_view(view, request)
        res = view.get_context_data()
        assert_is_instance(res['form'], NodeForm)
        assert_is_instance(res['view'], NodeFormView)
        assert_is_none(res['guid_object'])

    def test_context_data_load(self):
        node = NodeFactory()
        guid = node._id
        request = RequestFactory().get('/fake-path/?guid={}'.format(guid))
        view = NodeFormView()
        view = setup_view(view, request)
        res = view.get_context_data()
        assert_is_instance(res['form'], NodeForm)
        assert_is_instance(res['view'], NodeFormView)
        assert_is_instance(res['guid_object'], dict)
