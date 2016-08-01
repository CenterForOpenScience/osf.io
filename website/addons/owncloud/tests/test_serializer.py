# -*- coding: utf-8 -*-

from nose.tools import *  # noqa
import mock

from tests.factories import AuthUserFactory

from framework.auth import Auth

from website.addons.base.testing.serializers import OAuthAddonSerializerTestSuiteMixin
from website.addons.owncloud.tests.utils import (
    create_mock_owncloud, OwnCloudAddonTestCase
)
from website.addons.owncloud.utils import ExternalAccountConverter
from website.addons.owncloud.serializer import OwnCloudSerializer
from website.addons.owncloud.model import OwnCloudProvider
from website.addons.owncloud.tests.factories import OwnCloudAccountFactory
from website.util import api_url_for


class TestOwnCloudSerializer(OwnCloudAddonTestCase, OAuthAddonSerializerTestSuiteMixin):
    addon_short_name = 'owncloud'

    Serializer = OwnCloudSerializer
    ExternalAccountFactory = OwnCloudAccountFactory
    client =OwnCloudProvider

    required_settings = ('userIsOwner', 'nodeHasAuth', 'urls', 'userHasAuth')
    required_settings_authorized = ('ownerName', )

    def setUp(self):
        super(TestOwnCloudSerializer, self).setUp()
        self.ser = self.Serializer(
            user_settings=self.user_settings,
            node_settings=self.node_settings
        )
        converter =ExternalAccountConverter(self.node_settings.external_account)
        self.mock_api = mock.patch('website.addons.owncloud')
        self.mock_api.return_value = create_mock_owncloud(converter.host, converter.username, converter.password)
        self.mock_api.start()

    def tearDown(self):
        self.mock_api.stop()
        super(TestOwnCloudSerializer, self).tearDown()

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
