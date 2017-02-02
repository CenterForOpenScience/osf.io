# -*- coding: utf-8 -*-
from nose.tools import *  # noqa
import mock
import pytest


from addons.base.tests.serializers import OAuthAddonSerializerTestSuiteMixin
from addons.dataverse.tests.utils import create_mock_connection
from addons.dataverse.models import DataverseProvider
from addons.dataverse.tests.factories import DataverseAccountFactory
from tests.base import OsfTestCase

from addons.dataverse.serializer import DataverseSerializer

pytestmark = pytest.mark.django_db

class TestDataverseSerializer(OAuthAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'dataverse'

    Serializer = DataverseSerializer
    ExternalAccountFactory = DataverseAccountFactory
    client = DataverseProvider

    required_settings = ('userIsOwner', 'nodeHasAuth', 'urls', 'userHasAuth')
    required_settings_authorized = ('ownerName', )

    def setUp(self):
        super(TestDataverseSerializer, self).setUp()
        self.ser = self.Serializer(
            user_settings=self.user_settings,
            node_settings=self.node_settings
        )
        self.mock_api = mock.patch('addons.dataverse.serializer.client.connect_from_settings')
        self.mock_api.return_value = create_mock_connection()
        self.mock_api.start()

    def tearDown(self):
        self.mock_api.stop()
        super(TestDataverseSerializer, self).tearDown()

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
