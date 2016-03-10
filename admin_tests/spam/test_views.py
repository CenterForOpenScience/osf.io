from django.test import Client
from django.db import transaction
from nose import tools as nt
import mock

from tests.base import AdminTestCase
from tests.factories import CommentFactory
from admin_tests.utilities import setup_form_view

from admin.spam.views import SpamDetail
from admin.spam.forms import ConfirmForm
from admin.common_auth.logs import OSFLogEntry


class TestSpamDetail(AdminTestCase):
    def setUp(self):
        super(TestSpamDetail, self).setUp()
        self.request = Client().get('/fake_path')
        self.comment = CommentFactory()

    @mock.patch('admin.spam.views.SpamDetail.success_url')
    def test_form_log(self, mock_success_url):
        form_data = {'confirm': '2'}
        form = ConfirmForm(data=form_data)
        nt.assert_true(form.is_valid())
        view = SpamDetail()
        view = setup_form_view(
            view, self.request, form, spam_id=self.comment._id)
        with transaction.atomic():
            view.form_valid(form)
        obj = OSFLogEntry.objects.latest(field_name='action_time')
        nt.assert_equal(obj.object_id, self.comment._id)
