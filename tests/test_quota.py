# -*- coding: utf-8 -*-
import datetime
from nose.tools import *  # noqa (PEP8 asserts)
import pytest

from addons.osfstorage.models import OsfStorageFileNode
from osf.models import FileInfo
from osf_tests.factories import ProjectFactory, UserFactory
from tests.base import OsfTestCase
from website.util import quota


class QuotaTestCase(OsfTestCase):
    def setUp(self):
        super(QuotaTestCase, self).setUp()
        self.user = UserFactory()
        self.node = [
            ProjectFactory(creator=self.user),
            ProjectFactory(creator=self.user)
        ]

    def tearDown(self):
        super(QuotaTestCase, self).tearDown()

    # @pytest.mark.skip('Not yet implemented')
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

    # @pytest.mark.skip('Not yet implemented')
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
