# -*- coding: utf-8 -*-
import mock
from nose.tools import * # noqa
import pytest

from api.base import settings as api_settings
from tests.base import OsfTestCase
from osf.models import UserQuota
from osf_tests.factories import AuthUserFactory
from website.util import web_url_for, quota


@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestQuotaProfileView(OsfTestCase):
    def setUp(self):
        super(TestQuotaProfileView, self).setUp()
        self.user = AuthUserFactory()
        self.quota_text = '{}%, {}[{}] / {}[GB]'

    @mock.patch('website.util.quota.used_quota')
    def test_default_quota(self, mock_usedquota):
        mock_usedquota.return_value = 0

        response = self.app.get(
            web_url_for('profile_view_id', uid=self.user._id),
            auth=self.user.auth
        )
        expected = self.quota_text.format(0.0, 0, 'B', api_settings.DEFAULT_MAX_QUOTA)
        assert_in(expected, response.body)

    @mock.patch('website.util.quota.used_quota')
    def test_custom_quota(self, mock_usedquota):
        mock_usedquota.return_value = 0

        UserQuota.objects.create(user=self.user, max_quota=200)
        response = self.app.get(
            web_url_for('profile_view_id', uid=self.user._id),
            auth=self.user.auth
        )
        assert_in(self.quota_text.format(0.0, 0, 'B', 200), response.body)

    @mock.patch('website.util.quota.used_quota')
    def test_used_quota_bytes(self, mock_usedquota):
        mock_usedquota.return_value = 560

        UserQuota.objects.create(user=self.user, max_quota=100)
        response = self.app.get(
            web_url_for('profile_view_id', uid=self.user._id),
            auth=self.user.auth
        )
        assert_in(self.quota_text.format(0.0, 560, 'B', 100), response.body)

    @mock.patch('website.util.quota.used_quota')
    def test_used_quota_giga(self, mock_usedquota):
        mock_usedquota.return_value = 5.2 * 1024 ** 3

        UserQuota.objects.create(user=self.user, max_quota=100)
        response = self.app.get(
            web_url_for('profile_view_id', uid=self.user._id),
            auth=self.user.auth
        )
        assert_in(self.quota_text.format(5.2, 5.2, 'GB', 100), response.body)


class TestQuotaUtils(OsfTestCase):
    def setUp(self):
        super(TestQuotaUtils, self).setUp()

    def test_abbreviate_byte(self):
        abbr_size = quota.abbreviate_size(512)
        assert_equal(abbr_size[0], 512)
        assert_equal(abbr_size[1], 'B')

    def test_abbreviate_kilobyte(self):
        abbr_size = quota.abbreviate_size(512 * 1024)
        assert_equal(abbr_size[0], 512)
        assert_equal(abbr_size[1], 'KB')

    def test_abbreviate_megabyte(self):
        abbr_size = quota.abbreviate_size(512 * 1024 ** 2)
        assert_equal(abbr_size[0], 512)
        assert_equal(abbr_size[1], 'MB')

    def test_abbreviate_gigabyte(self):
        abbr_size = quota.abbreviate_size(512 * 1024 ** 3)
        assert_equal(abbr_size[0], 512)
        assert_equal(abbr_size[1], 'GB')

    def test_abbreviate_terabyte(self):
        abbr_size = quota.abbreviate_size(512 * 1024 ** 4)
        assert_equal(abbr_size[0], 512)
        assert_equal(abbr_size[1], 'TB')
