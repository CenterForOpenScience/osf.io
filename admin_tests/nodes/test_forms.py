from nose.tools import *  # flake8: noqa

from tests.base import AdminTestCase

from admin.nodes.forms import NodeForm


class NodeFormsTests(AdminTestCase):
    def setUp(self):
        super(NodeFormsTests, self).setUp()

    def test_valid_data(self):
        guid = '12345'
        form = NodeForm({
            'guid': guid,
        })
        assert_true(form.is_valid())
        assert_equal(form.cleaned_data.get('guid'), guid)

    def test_blank_data(self):
        form = NodeForm({})
        assert_false(form.is_valid())
        assert_equal(form.errors, {
            'guid': [u'This field is required.'],
        })
