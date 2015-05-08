# -*- coding: utf-8 -*-

import nose
from nose.tools import *  # noqa
import mock

import httplib as http
from tests.factories import AuthUserFactory

from dataverse.exceptions import UnauthorizedError

from framework.auth.decorators import Auth

from website.util import api_url_for, web_url_for
from website.addons.dataverse.settings import HOST
from website.addons.dataverse.views.config import serialize_settings
from website.addons.dataverse.tests.utils import (
    create_mock_connection, DataverseAddonTestCase,
)


class TestDataverseViewsAuth(DataverseAddonTestCase):

    def test_deauthorize(self):
        url = api_url_for('deauthorize_dataverse',
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
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dataverse_node_deauthorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(log_params['project'], None)

    def test_delete_user(self):
        url = api_url_for('dataverse_delete_user')

        # User without add-on can't delete
        user2 = AuthUserFactory()
        res = self.app.delete_json(url, auth=user2.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        self.user_settings.reload()
        assert_true(self.user_settings.api_token)

        # Aurthoized user can delete
        self.app.delete_json(url, auth=self.user.auth)

        # User is no longer authorized
        self.user_settings.reload()
        assert_false(self.user_settings.api_token)

        # User's authorized nodes are now deauthorized
        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.dataset_doi)
        assert_false(self.node_settings.dataset)
        assert_false(self.node_settings.user_settings)

    @mock.patch('website.addons.dataverse.views.auth.connect_from_settings_or_401')
    def test_user_config_get(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_user_config_get')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_true(result['connected'])
        assert_true(result['userHasAuth'])
        assert_equal(result['apiToken'], self.user_settings.api_token)
        assert_in('create', result['urls'])
        assert_in('delete', result['urls'])

    @mock.patch('website.addons.dataverse.views.auth.connect_from_settings_or_401')
    def test_user_config_get_no_connection(self, mock_connection):
        mock_connection.return_value = None

        url = api_url_for('dataverse_user_config_get')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_false(result['connected'])
        assert_true(result['userHasAuth'])
        assert_equal(result['apiToken'], self.user_settings.api_token)
        assert_in('create', result['urls'])
        assert_in('delete', result['urls'])


class TestDataverseViewsConfig(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_returns_correct_auth_info(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = serialize_settings(self.node_settings, self.user)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_non_owner(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        # Non-owner user without add-on
        stranger = AuthUserFactory()
        result = serialize_settings(self.node_settings, stranger)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_false(result['userHasAuth'])
        assert_false(result['userIsOwner'])

        # Non-owner user with add-on
        stranger.add_addon('dataverse')
        stranger_settings = stranger.get_addon('dataverse')
        stranger_settings.api_token = 'foo-bar'
        stranger_settings.save()
        result = serialize_settings(self.node_settings, stranger)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_false(result['userIsOwner'])

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_returns_correct_urls(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = serialize_settings(self.node_settings, self.user)
        urls = result['urls']

        assert_equal(urls['set'], self.project.api_url_for('set_dataverse_and_dataset'))
        assert_equal(urls['importAuth'], self.project.api_url_for('dataverse_import_user_auth'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('deauthorize_dataverse'))
        assert_equal(urls['getDatasets'], self.project.api_url_for('dataverse_get_datasets'))
        assert_equal(urls['datasetPrefix'], 'http://dx.doi.org/')
        assert_equal(urls['dataversePrefix'], 'http://{0}/dataverse/'.format(HOST))
        assert_equal(urls['owner'], web_url_for('profile_view_id', uid=self.user._primary_key))

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_returns_dv_info(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = serialize_settings(self.node_settings, self.user)

        assert_equal(len(result['dataverses']), 3)
        assert_equal(result['savedDataverse']['title'], self.node_settings.dataverse)
        assert_equal(result['savedDataverse']['alias'], self.node_settings.dataverse_alias)
        assert_equal(result['savedDataset']['title'], self.node_settings.dataset)
        assert_equal(result['savedDataset']['doi'], self.node_settings.dataset_doi)

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_serialize_settings_helper_no_connection(self, mock_connection):
        mock_connection.return_value = None

        result = serialize_settings(self.node_settings, self.user)

        assert_false(result['dataverses'])
        assert_equal(result['savedDataverse']['title'], self.node_settings.dataverse)
        assert_equal(result['savedDataverse']['alias'], self.node_settings.dataverse_alias)
        assert_equal(result['savedDataset']['title'], self.node_settings.dataset)
        assert_equal(result['savedDataset']['doi'], self.node_settings.dataset_doi)

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_dataverse_get_datasets(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_get_datasets', pid=self.project._primary_key)
        params = {'alias': 'ALIAS1'}
        res = self.app.post_json(url, params, auth=self.user.auth)

        assert_equal(len(res.json['datasets']), 3)
        first = res.json['datasets'][0]
        assert_equal(first['title'], 'Example (DVN/00001)')
        assert_equal(first['doi'], 'doi:12.3456/DVN/00001')

    @mock.patch('website.addons.dataverse.views.config.client._connect')
    def test_set_user_config(self, mock_connection):

        mock_connection.return_value = create_mock_connection()

        # Create a user with no settings
        user = AuthUserFactory()
        user.add_addon('dataverse')
        user_settings = user.get_addon('dataverse')

        url = api_url_for('dataverse_set_user_config')
        params = {'api_token': 'snowman-frosty'}

        # Post dataverse credentials
        self.app.post_json(url, params, auth=user.auth)
        user_settings.reload()

        # User settings have updated correctly
        assert_equal(user_settings.api_token, 'snowman-frosty')

    @mock.patch('website.addons.dataverse.views.config.client._connect')
    def test_set_user_config_fail(self, mock_connection):

        mock_connection.side_effect = UnauthorizedError('Bad credentials!')

        # Create a user with no settings
        user = AuthUserFactory()
        user.add_addon('dataverse')
        user_settings = user.get_addon('dataverse')

        url = api_url_for('dataverse_set_user_config')
        params = {'api_token': 'wrong-info'}

        # Post incorrect credentials to existing user
        res = self.app.post_json(url, params, auth=self.user.auth,
                                 expect_errors=True)
        self.user_settings.reload()

        # Original user's info has not changed
        assert_equal(res.status_code, http.UNAUTHORIZED)
        assert_equal(self.user_settings.api_token, 'snowman-frosty')

        # Post incorrect credentials to new user
        res = self.app.post_json(url, params, auth=user.auth,
                                 expect_errors=True)
        user_settings.reload()

        # New user's incorrect credentials were not saved
        assert_equal(res.status_code, http.UNAUTHORIZED)
        assert_equal(user_settings.api_token, None)

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_set_dataverse_and_dataset(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('set_dataverse_and_dataset',
                          pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS3'},
            'dataset': {'doi': 'doi:12.3456/DVN/00003'},
        }

        # Select a different dataset
        self.app.post_json(url, params, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        # New dataset was selected
        assert_equal(self.node_settings.dataverse_alias, 'ALIAS3')
        assert_equal(self.node_settings.dataset, 'Example (DVN/00003)')
        assert_equal(self.node_settings.dataset_doi, 'doi:12.3456/DVN/00003')
        assert_equal(self.node_settings.dataset_id, '18')

        # Log states that a dataset was selected
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dataverse_dataset_linked')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_is_none(log_params['project'])
        assert_equal(log_params['dataset'], 'Example (DVN/00003)')

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_set_dataverse_no_dataset(self, mock_connection):
        mock_connection.return_value = create_mock_connection()
        num_old_logs = len(self.project.logs)

        url = api_url_for('set_dataverse_and_dataset',
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
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(self.node_settings.dataverse_alias, 'ALIAS2')
        assert_equal(self.node_settings.dataset, 'Example (DVN/00001)')
        assert_equal(self.node_settings.dataset_doi, 'doi:12.3456/DVN/00001')

        # Nothing was logged
        self.project.reload()
        assert_equal(len(self.project.logs), num_old_logs)


class TestDataverseViewsHgrid(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_published(self, mock_files, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_files.return_value = ['mock_file']

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_root_folder_public',
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

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_not_published(self, mock_files, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_files.return_value = []

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_root_folder_public',
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


    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_no_connection(self, mock_files, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_files.return_value = ['mock_file']

        url = api_url_for('dataverse_root_folder_public',
                          pid=self.project._primary_key)

        mock_connection.return_value = None
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])

    def test_dataverse_root_incomplete(self):
        self.node_settings.dataset_doi = None
        self.node_settings.save()

        url = api_url_for('dataverse_root_folder_public',
                  pid=self.project._primary_key)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])


class TestDataverseViewsCrud(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_401')
    @mock.patch('website.addons.dataverse.views.crud.publish_dataset')
    def test_dataverse_publish_dataset(self, mock_publish, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_publish_dataset',
                          pid=self.project._primary_key)
        self.app.put(url, auth=self.user.auth)
        assert_true(mock_publish.called)

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_401')
    @mock.patch('website.addons.dataverse.views.crud.publish_dataset')
    @mock.patch('website.addons.dataverse.views.crud.publish_dataverse')
    def test_dataverse_publish_both(self, mock_publish_dv, mock_publish_ds, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_publish_both',
                          pid=self.project._primary_key)
        self.app.put(url, auth=self.user.auth)
        assert_true(mock_publish_dv.called)
        assert_true(mock_publish_ds.called)


class TestDataverseRestrictions(DataverseAddonTestCase):

    def setUp(self):

        super(DataverseAddonTestCase, self).setUp()

        # Nasty contributor who will try to access content that he shouldn't
        # have access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_restricted_set_dataset_not_owner(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        # Contributor has dataverse auth, but is not the node authorizer
        self.contrib.add_addon('dataverse')
        self.contrib.save()

        url = api_url_for('set_dataverse_and_dataset', pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS1'},
            'dataset': {'doi': 'doi:12.3456/DVN/00002'},
        }
        res = self.app.post_json(url, params, auth=self.contrib.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)


if __name__ == '__main__':
    nose.run()
