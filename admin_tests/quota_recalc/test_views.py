# -*- coding: utf-8 -*-
from django.test import RequestFactory
import json
import mock
from nose import tools as nt

from admin.quota_recalc import views
from api.base import settings as api_settings
from osf.models import UserQuota
from osf_tests.factories import AuthUserFactory
from tests.base import AdminTestCase


class TestQuotaRecalcView(AdminTestCase):
    @staticmethod
    def get_request(view, **kwargs):
        return view(RequestFactory().get('/fake_path'), **kwargs)

    @mock.patch('admin.quota_recalc.views.used_quota')
    def test_user_create_userquota_record(self, mock_usedquota):
        mock_usedquota.return_value = 1500

        user = AuthUserFactory()
        UserQuota.objects.filter(user=user).delete()
        response = self.get_request(views.user, guid=user._id)
        res_json = json.loads(response.content)
        nt.assert_equal(response.status_code, 200)
        nt.assert_equal(res_json['status'], 'OK')

        user_quota = UserQuota.objects.get(user=user, storage_type=UserQuota.NII_STORAGE)
        nt.assert_equal(user_quota.max_quota, api_settings.DEFAULT_MAX_QUOTA)
        nt.assert_equal(user_quota.used, 1500)

    @mock.patch('admin.quota_recalc.views.used_quota')
    def test_user_update_userquota_record(self, mock_usedquota):
        mock_usedquota.return_value = 7000

        user = AuthUserFactory()
        UserQuota.objects.create(
            user=user,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=200,
            used=5000
        )
        response = self.get_request(views.user, guid=user._id)
        res_json = json.loads(response.content)
        nt.assert_equal(response.status_code, 200)
        nt.assert_equal(res_json['status'], 'OK')

        user_quota = UserQuota.objects.get(user=user, storage_type=UserQuota.NII_STORAGE)
        nt.assert_equal(user_quota.max_quota, 200)
        nt.assert_equal(user_quota.used, 7000)

    @mock.patch('admin.quota_recalc.views.used_quota')
    def test_user_invalid_guid(self, mock_usedquota):
        mock_usedquota.return_value = 3000

        response = self.get_request(views.user, guid='cuzidontcare')
        res_json = json.loads(response.content)
        nt.assert_equal(response.status_code, 404)
        nt.assert_equal(res_json['status'], 'failed')
        nt.assert_equal(res_json['message'], 'User not found.')

    @mock.patch('admin.quota_recalc.views.used_quota')
    def test_users_create_userquota_record(self, mock_usedquota):
        mock_usedquota.return_value = 1500
        user = AuthUserFactory()
        user2 = AuthUserFactory()
        UserQuota.objects.filter(user=user).delete()
        UserQuota.objects.filter(user=user2).delete()
        response = self.get_request(views.user, guid=user._id)
        res_json = json.loads(response.content)
        nt.assert_equal(response.status_code, 200)
        nt.assert_equal(res_json['status'], 'OK')

        response2 = self.get_request(views.user, guid=user2._id)
        res_json2 = json.loads(response2.content)
        nt.assert_equal(response2.status_code, 200)
        nt.assert_equal(res_json2['status'], 'OK')
        user_quota2 = UserQuota.objects.get(user=user2, storage_type=UserQuota.NII_STORAGE)
        nt.assert_equal(user_quota2.max_quota, api_settings.DEFAULT_MAX_QUOTA)
        nt.assert_equal(user_quota2.used, 1500)

        response3 = self.get_request(views.all_users)
        res_json3 = json.loads(response3.content)
        nt.assert_equal(response3.status_code, 200)
        nt.assert_equal(res_json3['status'], 'OK')
        nt.assert_true('2' in res_json3['message'])
