from nose.tools import *  # noqa: F403

from tests.base import AdminTestCase

from admin.base.forms import GuidForm


class TestGuidForm(AdminTestCase):
    def setUp(self):
        super().setUp()

    def test_valid_data(self):
        guid = '12345'
        form = GuidForm({
            'guid': guid,
        })
        assert_true(form.is_valid())
        assert_equal(form.cleaned_data.get('guid'), guid)

    def test_blank_data(self):
        form = GuidForm({})
        assert_false(form.is_valid())
        assert_equal(form.errors, {
            'guid': ['This field is required.'],
        })
