# -*- coding: utf-8 -*-
from nose.tools import (assert_false, assert_equal, assert_in, assert_true)
import mock
import pytest
import unittest

from rest_framework import status as http_status


from addons.base.tests.views import OAuthAddonConfigViewsTestCaseMixin
from addons.dataverse.models import DataverseProvider
from addons.dataverse.tests.utils import (
    create_mock_connection, DataverseAddonTestCase, create_external_account,
)
from framework.auth.decorators import Auth
from osf_tests.factories import AuthUserFactory
from tests.base import OsfTestCase
from addons.dataverse.serializer import DataverseSerializer
from website.util import api_url_for

pytestmark = pytest.mark.django_db

class TestAuthViews(DataverseAddonTestCase, OsfTestCase, unittest.TestCase):

    def test_deauthorize(self):
        url = api_url_for('dataverse_deauthorize_node',
                          pid=self.project._primary_key)
        self.app.delete(url, auth=self.user.auth)

        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.dataset_doi)
        assert_false(self.node_settings.dataset)
        assert_false(self.node_settings.user_settings)

        # Log states that node was deauthorized
        self.project.reload()
        last_log = self.project.logs.latest()
        assert_equal(last_log.action, 'dataverse_node_deauthorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(log_params['project'], None)

    def test_user_config_get(self):
        url = api_url_for('dataverse_user_config_get')
        new_user = AuthUserFactory()
        res = self.app.get(url, auth=new_user.auth)

        result = res.json.get('result')
        assert_false(result['userHasAuth'])
        assert_in('hosts', result)
        assert_in('create', result['urls'])

        # userHasAuth is true with external accounts
        new_user.external_accounts.add(create_external_account())
        new_user.save()
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_true(result['userHasAuth'])

class TestConfigViews(DataverseAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    connection = create_mock_connection()
    Serializer = DataverseSerializer
    client = DataverseProvider

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_ser_api = mock.patch('addons.dataverse.serializer.client.connect_from_settings')
        self.mock_ser_api.return_value = create_mock_connection()
        self.mock_ser_api.start()

    def tearDown(self):
        self.mock_ser_api.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    def test_folder_list(self, mock_connection):
        #test_get_datasets
        mock_connection.return_value = self.connection

        url = api_url_for('dataverse_get_datasets', pid=self.project._primary_key)
        params = {'alias': 'ALIAS1'}
        res = self.app.post_json(url, params, auth=self.user.auth)

        assert_equal(len(res.json['datasets']), 3)
        first = res.json['datasets'][0]
        assert_equal(first['title'], 'Example (DVN/00001)')
        assert_equal(first['doi'], 'doi:12.3456/DVN/00001')

    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    def test_set_config(self, mock_connection):
        mock_connection.return_value = self.connection

        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.post_json(url, {
            'dataverse': {'alias': 'ALIAS3'},
            'dataset': {'doi': 'doi:12.3456/DVN/00003'},
        }, auth=self.user.auth)
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.project.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_dataset_linked'.format(self.ADDON_SHORT_NAME)
        )
        assert_equal(res.json['dataverse'], self.connection.get_dataverse('ALIAS3').title)
        assert_equal(res.json['dataset'],
            self.connection.get_dataverse('ALIAS3').get_dataset_by_doi('doi:12.3456/DVN/00003').title)

    def test_get_config(self):
        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        assert_in('result', res.json)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
        )
        assert_equal(serialized, res.json['result'])

    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    def test_set_config_no_dataset(self, mock_connection):
        mock_connection.return_value = self.connection
        num_old_logs = self.project.logs.count()

        url = api_url_for('dataverse_set_config',
                          pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS3'},
            'dataset': {},    # The dataverse has no datasets
        }

        # Select a different dataset
        res = self.app.post_json(url, params, auth=self.user.auth,
                                 expect_errors=True)
        self.node_settings.reload()

        # Old settings did not change
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)
        assert_equal(self.node_settings.dataverse_alias, 'ALIAS2')
        assert_equal(self.node_settings.dataset, 'Example (DVN/00001)')
        assert_equal(self.node_settings.dataset_doi, 'doi:12.3456/DVN/00001')

        # Nothing was logged
        self.project.reload()
        assert_equal(self.project.logs.count(), num_old_logs)


class TestHgridViews(DataverseAddonTestCase, OsfTestCase, unittest.TestCase):

    @mock.patch('addons.dataverse.views.client.get_custom_publish_text')
    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    @mock.patch('addons.dataverse.views.client.get_files')
    def test_dataverse_root_published(self, mock_files, mock_connection, mock_text):
        mock_connection.return_value = create_mock_connection()
        mock_files.return_value = ['mock_file']
        mock_text.return_value = 'Do you want to publish?'

        self.project.set_privacy('public')
        self.project.save()

        alias = self.node_settings.dataverse_alias
        doi = self.node_settings.dataset_doi
        external_account = create_external_account()
        self.user.external_accounts.add(external_account)
        self.user.save()
        self.node_settings.set_auth(external_account, self.user)
        self.node_settings.dataverse_alias = alias
        self.node_settings.dataset_doi = doi
        self.node_settings.save()

        url = api_url_for('dataverse_root_folder',
                          pid=self.project._primary_key)

        # Contributor can select between states, current state is correct
        res = self.app.get(url, auth=self.user.auth)
        assert_true(res.json[0]['permissions']['edit'])
        assert_true(res.json[0]['hasPublishedFiles'])
        assert_equal(res.json[0]['version'], 'latest-published')

        # Non-contributor gets published version, no options
        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_false(res.json[0]['permissions']['edit'])
        assert_true(res.json[0]['hasPublishedFiles'])
        assert_equal(res.json[0]['version'], 'latest-published')

    @mock.patch('addons.dataverse.views.client.get_custom_publish_text')
    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    @mock.patch('addons.dataverse.views.client.get_files')
    def test_dataverse_root_not_published(self, mock_files, mock_connection, mock_text):
        mock_connection.return_value = create_mock_connection()
        mock_files.return_value = []
        mock_text.return_value = 'Do you want to publish?'

        self.project.set_privacy('public')
        self.project.save()

        alias = self.node_settings.dataverse_alias
        doi = self.node_settings.dataset_doi
        external_account = create_external_account()
        self.user.external_accounts.add(external_account)
        self.user.save()
        self.node_settings.set_auth(external_account, self.user)
        self.node_settings.dataverse_alias = alias
        self.node_settings.dataset_doi = doi
        self.node_settings.save()

        url = api_url_for('dataverse_root_folder',
                          pid=self.project._primary_key)

        # Contributor gets draft, no options
        res = self.app.get(url, auth=self.user.auth)
        assert_true(res.json[0]['permissions']['edit'])
        assert_false(res.json[0]['hasPublishedFiles'])
        assert_equal(res.json[0]['version'], 'latest')

        # Non-contributor gets nothing
        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_equal(res.json, [])

    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    @mock.patch('addons.dataverse.views.client.get_files')
    def test_dataverse_root_no_connection(self, mock_files, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_files.return_value = ['mock_file']

        url = api_url_for('dataverse_root_folder',
                          pid=self.project._primary_key)

        mock_connection.return_value = None
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])

    def test_dataverse_root_incomplete(self):
        self.node_settings.dataset_doi = None
        self.node_settings.save()

        url = api_url_for('dataverse_root_folder',
                  pid=self.project._primary_key)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])


class TestCrudViews(DataverseAddonTestCase, OsfTestCase, unittest.TestCase):

    @mock.patch('addons.dataverse.views.client.connect_from_settings_or_401')
    @mock.patch('addons.dataverse.views.client.publish_dataset')
    @mock.patch('addons.dataverse.views.client.publish_dataverse')
    def test_dataverse_publish_dataset(self, mock_publish_dv, mock_publish_ds, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_publish_dataset',
                          pid=self.project._primary_key)
        self.app.put_json(url, params={'publish_both': False}, auth=self.user.auth)

        # Only dataset was published
        assert_false(mock_publish_dv.called)
        assert_true(mock_publish_ds.called)

    @mock.patch('addons.dataverse.views.client.connect_from_settings_or_401')
    @mock.patch('addons.dataverse.views.client.publish_dataset')
    @mock.patch('addons.dataverse.views.client.publish_dataverse')
    def test_dataverse_publish_both(self, mock_publish_dv, mock_publish_ds, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_publish_dataset',
                          pid=self.project._primary_key)
        self.app.put_json(url, params={'publish_both': True}, auth=self.user.auth)

        # Both Dataverse and dataset were published
        assert_true(mock_publish_dv.called)
        assert_true(mock_publish_ds.called)


class TestDataverseRestrictions(DataverseAddonTestCase, OsfTestCase):

    def setUp(self):

        super(DataverseAddonTestCase, self).setUp()

        # Nasty contributor who will try to access content that he shouldn't
        # have access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()

    @mock.patch('addons.dataverse.views.client.connect_from_settings')
    def test_restricted_set_dataset_not_owner(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        # Contributor has dataverse auth, but is not the node authorizer
        self.contrib.add_addon('dataverse')
        self.contrib.save()

        url = api_url_for('dataverse_set_config', pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS1'},
            'dataset': {'doi': 'doi:12.3456/DVN/00002'},
        }
        res = self.app.post_json(url, params, auth=self.contrib.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)
