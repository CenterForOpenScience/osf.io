from nose import tools as nt
import mock
import json
from django.test import Client

from tests.base import AdminTestCase
from admin_tests.factories import UserFactory

from admin.pre_reg.views import approve_draft, reject_draft, update_draft
from admin.common_auth.logs import OSFLogEntry


class TestPreReg(AdminTestCase):
    def setUp(self):
        super(TestPreReg, self).setUp()
        self.request = Client().post('/fake-path')
        self.request.user = UserFactory
        self.request.POST = dict()
        self.request.body = json.dumps(dict())

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

    @mock.patch('admin.pre_reg.views.DraftRegistration.update_metadata')
    @mock.patch('admin.pre_reg.views.DraftRegistration.save')
    @mock.patch('admin.pre_reg.views.csrf_exempt')
    @mock.patch('admin.pre_reg.views.get_draft_or_error')
    @mock.patch('admin.pre_reg.views.serializers.serialize_draft_registration')
    @mock.patch('admin.pre_reg.views.JsonResponse')
    def test_add_log_update(self, mock_1, mock_2, mock_3, mock_4, mock_5, mock_6):
        count = OSFLogEntry.objects.count()
        update_draft(self.request, 1)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)
