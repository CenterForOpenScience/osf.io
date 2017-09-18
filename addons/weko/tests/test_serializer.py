# -*- coding: utf-8 -*-
"""Serializer tests for the WEKO addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.util import web_url_for
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.weko.tests.factories import WEKOAccountFactory
from addons.weko.serializer import WEKOSerializer

from tests.base import OsfTestCase
from addons.weko.tests.utils import ConnectionMock

class TestWEKOSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'weko'
    Serializer = WEKOSerializer
    ExternalAccountFactory = WEKOAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.index_id = pid

    def setUp(self):
        self.mock_connect_or_error = mock.patch('addons.weko.client.connect_or_error')
        self.mock_connect_or_error.return_value = ConnectionMock()
        self.mock_connect_or_error.start()
        self.mock_connect_from_settings = mock.patch('addons.weko.client.connect_from_settings')
        self.mock_connect_from_settings.return_value = ConnectionMock()
        self.mock_connect_from_settings.start()
        super(TestWEKOSerializer, self).setUp()

    def tearDown(self):
        self.mock_connect_or_error.stop()
        self.mock_connect_from_settings.stop()
        super(TestWEKOSerializer, self).tearDown()

    def test_serialize_acccount(self):
        ea = self.ExternalAccountFactory()
        expected = {
            'id': ea._id,
            'provider_id': ea.provider_id,
            'provider_name': ea.provider_name,
            'provider_short_name': ea.provider,
            'display_name': ea.display_name,
            'profile_url': ea.profile_url,
            'nodes': [],
            'host': ea.oauth_key,
        }
        assert_equal(self.ser.serialize_account(ea), expected)

    def test_serialize_settings_authorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        for key in self.required_settings:
            assert_in(key, serialized)
        assert_in('owner', serialized['urls'])
        assert_equal(serialized['urls']['owner'], web_url_for(
            'profile_view_id',
            uid=self.user_settings.owner._id
        ))
        assert_in('ownerName', serialized)
        assert_equal(serialized['ownerName'], self.user_settings.owner.fullname)
        assert_in('savedIndex', serialized)

    def test_serialize_settings_authorized_folder_is_set(self):
        pass

    def test_serialize_settings_authorized_no_folder(self):
        pass
