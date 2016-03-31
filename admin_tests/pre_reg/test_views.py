from nose import tools as nt
import mock
from django.test import RequestFactory

from tests.base import AdminTestCase
from admin_tests.factories import UserFactory

from admin.pre_reg.views import approve_draft, reject_draft
from admin.common_auth.logs import OSFLogEntry


class TestPreReg(AdminTestCase):
    def setUp(self):
        super(TestPreReg, self).setUp()
        self.request = RequestFactory().post('/nothing', data={'bleh': 'arg'})
        self.request.user = UserFactory

    @mock.patch('admin.pre_reg.views.DraftRegistration.approve')
    @mock.patch('admin.pre_reg.views.csrf_exempt')
    @mock.patch('admin.pre_reg.views.get_draft_or_error')
    def test_add_log_approve(self, mock_1, mock_2, mock_3):
        count = OSFLogEntry.objects.count()
        approve_draft(self.request, 1)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)

    @mock.patch('admin.pre_reg.views.DraftRegistration.approve')
    @mock.patch('admin.pre_reg.views.csrf_exempt')
    @mock.patch('admin.pre_reg.views.get_draft_or_error')
    def test_add_log_reject(self, mock_1, mock_2, mock_3):
        count = OSFLogEntry.objects.count()
        reject_draft(self.request, 1)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)
