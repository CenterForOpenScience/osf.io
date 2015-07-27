import httplib as http

from nose.tools import *  # noqa
import mock

from framework.exceptions import HTTPError
from website.addons.dataverse.tests.utils import (
    create_mock_connection, DataverseAddonTestCase, create_external_account,
)
from website.addons.dataverse.provider import DataverseProvider


class TestDataverseSerializerConfig(DataverseAddonTestCase):

    def setUp(self):
        super(TestDataverseSerializerConfig, self).setUp()

        self.provider = DataverseProvider()

    def test_default(self):
        assert_is_none(self.provider.account)

    @mock.patch('website.addons.dataverse.client._connect')
    def test_add_user_auth(self, mock_connect):
        mock_connect.return_value = create_mock_connection()

        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.user.save()

        self.provider.add_user_auth(
            self.node_settings,
            self.user,
            external_account._id,
        )

        assert_equal(self.node_settings.external_account, external_account)
        assert_equal(self.node_settings.user_settings, self.user_settings)

    def test_add_user_auth_not_in_user_external_accounts(self):
        external_account = create_external_account()

        with assert_raises(HTTPError) as e:
            self.provider.add_user_auth(
                self.node_settings,
                self.user,
                external_account._id,
            )
            assert_equal(e.status_code, http.FORBIDDEN)
