# -*- coding: utf-8 -*-
import datetime
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest

from addons.osfstorage.models import OsfStorageFileNode
from api.base import settings as api_settings
from tests.base import OsfTestCase
from osf.models import FileInfo, UserQuota
from osf_tests.factories import AuthUserFactory, ProjectFactory, UserFactory
from website.util import web_url_for, quota


@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestQuotaProfileView(OsfTestCase):
    def setUp(self):
        super(TestQuotaProfileView, self).setUp()
        self.user = AuthUserFactory()
        self.quota_text = '{}%, {}[{}] / {}[GB]'

    def tearDown(self):
        super(TestQuotaProfileView, self).tearDown()

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


class TestAbbreviateSize(OsfTestCase):
    def setUp(self):
        super(TestAbbreviateSize, self).setUp()

    def tearDown(self):
        super(TestAbbreviateSize, self).tearDown()

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


class TestUsedQuota(OsfTestCase):
    def setUp(self):
        super(TestUsedQuota, self).setUp()
        self.user = UserFactory()
        self.node = [
            ProjectFactory(creator=self.user),
            ProjectFactory(creator=self.user)
        ]

    def tearDown(self):
        super(TestUsedQuota, self).tearDown()

    def test_calculate_used_quota(self):
        file_list = []

        # No files
        assert_equal(quota.used_quota(self.user._id), 0)

        # Add a file to node[0]
        file_list.append(OsfStorageFileNode.create(
            target=self.node[0],
            name='file0'
        ))
        file_list[0].save()
        FileInfo.objects.create(file=file_list[0], file_size=500)
        assert_equal(quota.used_quota(self.user._id), 500)

        # Add a file to node[1]
        file_list.append(OsfStorageFileNode.create(
            target=self.node[1],
            name='file1'
        ))
        file_list[1].save()
        FileInfo.objects.create(file=file_list[1], file_size=1000)
        assert_equal(quota.used_quota(self.user._id), 1500)

    def test_calculate_used_quota_deleted_file(self):
        # Add a (deleted) file to node[0]
        file_node = OsfStorageFileNode.create(
            target=self.node[0],
            name='file0',
            deleted_on=datetime.datetime.now(),
            deleted_by=self.user
        )
        file_node.save()
        FileInfo.objects.create(file=file_node, file_size=500)
        assert_equal(quota.used_quota(self.user._id), 0)
