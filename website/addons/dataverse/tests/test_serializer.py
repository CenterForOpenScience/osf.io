# -*- coding: utf-8 -*-

from nose.tools import *  # noqa
import mock

from tests.factories import AuthUserFactory


from website.util import api_url_for
from website.addons.dataverse.tests.utils import (
    create_mock_connection, DataverseAddonTestCase, create_external_account,
)
from website.addons.dataverse.serializer import DataverseSerializer


class TestDataverseSerializerConfig(DataverseAddonTestCase):

    def setUp(self):
        super(TestDataverseSerializerConfig, self).setUp()

        self.host = 'my.host.name'
        self.external_account = create_external_account(self.host)
        self.user.external_accounts.append(self.external_account)
        self.node_settings.set_auth(self.external_account, self.user)
        self.serializer = DataverseSerializer(
            user_settings=self.user_settings,
            node_settings=self.node_settings,
        )

    def test_serialize_account(self):

        ret = self.serializer.serialize_account(self.external_account)
        assert_equal(ret['host'], self.host)
        assert_equal(ret['host_url'], 'https://{0}'.format(self.host))

    def test_user_is_owner(self):

        # No user is not owner
        serializer = DataverseSerializer(node_settings=self.node_settings)
        assert_false(serializer.user_is_owner)

        # Different user is not owner
        serializer.user_settings = AuthUserFactory()
        assert_false(serializer.user_is_owner)

        # Owner is owner
        serializer.user_settings = self.user_settings
        assert_true(serializer.user_is_owner)

    def test_credentials_owner(self):
        assert_equal(self.node_settings.user_settings.owner, self.user)


    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_returns_correct_auth_info(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = self.serializer.serialized_node_settings
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_non_owner(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        # Non-owner user without add-on
        serializer = DataverseSerializer(node_settings=self.node_settings)
        result = serializer.serialized_node_settings
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_false(result['userHasAuth'])
        assert_false(result['userIsOwner'])

        # Non-owner user with add-on
        stranger = AuthUserFactory()
        stranger.add_addon('dataverse')
        stranger.external_accounts.append(create_external_account())
        serializer.user_settings = stranger.get_addon('dataverse')
        result = serializer.serialized_node_settings
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_false(result['userIsOwner'])

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_returns_correct_urls(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        # result =
        urls = self.serializer.serialized_urls

        assert_equal(urls['create'], api_url_for('dataverse_add_user_account'))
        assert_equal(urls['set'], self.project.api_url_for('dataverse_set_config'))
        assert_equal(urls['importAuth'], self.project.api_url_for('dataverse_add_user_auth'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('dataverse_remove_user_auth'))
        assert_equal(urls['getDatasets'], self.project.api_url_for('dataverse_get_datasets'))
        assert_equal(urls['datasetPrefix'], 'http://dx.doi.org/')
        assert_equal(urls['dataversePrefix'], 'http://{0}/dataverse/'.format(self.host))
        assert_equal(urls['accounts'], api_url_for('dataverse_get_user_accounts'))

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_returns_dv_info(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = self.serializer.serialized_node_settings

        assert_equal(len(result['dataverses']), 3)
        assert_true(result['connected'])
        assert_equal(result['dataverseHost'], self.host)
        assert_equal(result['savedDataverse']['title'], self.node_settings.dataverse)
        assert_equal(result['savedDataverse']['alias'], self.node_settings.dataverse_alias)
        assert_equal(result['savedDataset']['title'], self.node_settings.dataset)
        assert_equal(result['savedDataset']['doi'], self.node_settings.dataset_doi)

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_no_connection(self, mock_connection):
        mock_connection.return_value = None

        result = self.serializer.serialized_node_settings

        assert_false(result['dataverses'])
        assert_false(result['connected'])
        assert_equal(result['dataverseHost'], self.host)
        assert_equal(result['savedDataverse']['title'], self.node_settings.dataverse)
        assert_equal(result['savedDataverse']['alias'], self.node_settings.dataverse_alias)
        assert_equal(result['savedDataset']['title'], self.node_settings.dataset)
        assert_equal(result['savedDataset']['doi'], self.node_settings.dataset_doi)
