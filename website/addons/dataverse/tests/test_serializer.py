# -*- coding: utf-8 -*-

from nose.tools import *  # noqa
import mock

from tests.factories import AuthUserFactory

from framework.auth import Auth

from website.addons.base.testing.serializers import OAuthAddonSerializerTestSuiteMixin
from website.addons.dataverse.tests.utils import (
    create_mock_connection, DataverseAddonTestCase, create_external_account,
)
from website.addons.dataverse.serializer import DataverseSerializer
from website.addons.dataverse.model import DataverseProvider
from website.addons.dataverse.tests.factories import DataverseAccountFactory
from website.util import api_url_for


class TestDataverseSerializer(DataverseAddonTestCase, OAuthAddonSerializerTestSuiteMixin):
    addon_short_name = 'dataverse'
    
    Serializer = DataverseSerializer
    ExternalAccountFactory = DataverseAccountFactory
    client =DataverseProvider

    required_settings = ('userIsOwner', 'nodeHasAuth', 'urls', 'userHasAuth')
    required_settings_authorized = ('ownerName', )

    def setUp(self):
        super(TestDataverseSerializer, self).setUp()
        self.ser = self.Serializer(
            user_settings=self.user_settings,
            node_settings=self.node_settings
        )
        self.mock_api = mock.patch('website.addons.dataverse.serializer.client.connect_from_settings')
        self.mock_api.return_value = create_mock_connection()
        self.mock_api.start()

    def tearDown(self):
        self.mock_api.stop()
        super(TestDataverseSerializer, self).tearDown()

    def set_node_settings(self, user):
        self.node = self.project
        self.node_settings = self.node.get_or_add_addon(self.addon_short_name, auth=Auth(user))
        self.node_settings.set_auth(self.user_settings.external_accounts[0], self.user)

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
            'host_url': 'https://{0}'.format(ea.oauth_key),
        }
        assert_equal(self.ser.serialize_account(ea), expected)
