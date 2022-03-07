# -*- coding: utf-8 -*-
import mock
import pytest
from addons.osfstorage.models import OsfStorageFileNode
from nose.tools import *  # noqa (PEP8 asserts)
from osf.models import (
    FileInfo, UserQuota
)
from osf_tests.factories import ProjectFactory, UserFactory
from tests.base import OsfTestCase
from website.util import quota


@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestUpdateUserUsedQuota(OsfTestCase):
    def setUp(self):
        super(TestUpdateUserUsedQuota, self).setUp()
        self.user = UserFactory()
        self.user.save()
        self.user_quota = UserQuota.objects.create(user=self.user, storage_type=UserQuota.NII_STORAGE, max_quota=200,
                                                   used=1000)

        self.node = [
            ProjectFactory(creator=self.user),
            ProjectFactory(creator=self.user)
        ]

    def test_calculate_used_quota(self):
        file_list = []

        # No files
        assert_equal(quota.used_quota(self.user._id, storage_type=UserQuota.NII_STORAGE), 0)
        assert_equal(quota.used_quota(self.user._id, storage_type=UserQuota.CUSTOM_STORAGE), 0)

        # Add a file to node[0]
        file_list.append(OsfStorageFileNode.create(
            target=self.node[0],
            name='file0'
        ))
        file_list[0].save()
        FileInfo.objects.create(file=file_list[0], file_size=500)
        assert_equal(quota.used_quota(self.user._id, storage_type=UserQuota.NII_STORAGE), 500)
        assert_equal(quota.used_quota(self.user._id, storage_type=UserQuota.CUSTOM_STORAGE), 0)

        # Add a file to node[1]
        file_list.append(OsfStorageFileNode.create(
            target=self.node[1],
            name='file1'
        ))
        file_list[1].save()
        FileInfo.objects.create(file=file_list[1], file_size=1000)

        assert_equal(quota.used_quota(self.user._id, storage_type=UserQuota.NII_STORAGE), 1500)
        assert_equal(quota.used_quota(self.user._id, storage_type=UserQuota.CUSTOM_STORAGE), 0)

    @mock.patch.object(UserQuota, 'save')
    @mock.patch('website.util.quota.used_quota')
    def test_update_user_used_quota_method_with_user_quota_exist(self, mock_used, mock_user_quota_save):
        mock_used.return_value = 500
        quota.update_user_used_quota(
            user=self.user,
            storage_type=UserQuota.NII_STORAGE
        )

        mock_user_quota_save.assert_called()

    @mock.patch('website.util.quota.used_quota')
    def test_update_user_used_quota_method_with_user_quota_not_exist(self, mock_used):
        another_user = UserFactory()
        mock_used.return_value = 500

        quota.update_user_used_quota(
            user=another_user,
            storage_type=UserQuota.NII_STORAGE
        )

        user_quota = UserQuota.objects.filter(
            storage_type=UserQuota.NII_STORAGE,
        ).all()

        assert_equal(len(user_quota), 2)
        user_quota = user_quota.filter(user=another_user)
        assert_equal(len(user_quota), 1)
        user_quota = user_quota[0]
        assert_equal(user_quota.used, 500)
