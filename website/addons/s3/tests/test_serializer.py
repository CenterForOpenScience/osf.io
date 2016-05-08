# -*- coding: utf-8 -*-
"""Serializer tests for the S3 addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.util import web_url_for
from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.s3.tests.factories import S3AccountFactory
from website.addons.s3.serializer import S3Serializer

from tests.base import OsfTestCase


class TestS3Serializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 's3'
    Serializer = S3Serializer
    ExternalAccountFactory = S3AccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.bucket = pid

    def setUp(self):
        self.mock_can_list = mock.patch('website.addons.s3.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestS3Serializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestS3Serializer, self).tearDown()

    ## Overrides ##

    def test_serialize_settings_authorized(self):
        serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        for key in self.required_settings:
            assert_in(key, serialized)
        assert_in('owner', serialized['urls'])
        assert_equal(serialized['urls']['owner'], web_url_for(
            'profile_view_id',
            uid=self.user_settings.owner._id
        ))
        assert_in('ownerName', serialized)
        assert_in('encryptUploads', serialized)
        assert_equal(serialized['ownerName'], self.user_settings.owner.fullname)
        assert_in('bucket', serialized)

    def test_serialize_settings_authorized_no_folder(self):
        serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        assert_in('bucket', serialized)
        assert_in('encryptUploads', serialized)
        assert_equal(serialized['bucket'], '')
        assert_false(serialized['hasBucket'])

    def test_serialize_settings_authorized_folder_is_set(self):
        self.set_provider_id('foo')
        serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        assert_in('bucket', serialized)
        assert_equal(serialized['bucket'], 'foo')
        assert_true(serialized['hasBucket'])
        assert_in('encryptUploads', serialized)
