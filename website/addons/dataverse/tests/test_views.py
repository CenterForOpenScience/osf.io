# -*- coding: utf-8 -*-

import nose
from nose.tools import *  # noqa
import mock

import httplib as http
from tests.factories import AuthUserFactory

from dataverse.exceptions import UnauthorizedError

from framework.auth.decorators import Auth

from website.util import api_url_for
from website.addons.dataverse.serializer import DataverseSerializer
from website.addons.dataverse.tests.utils import (
    create_mock_connection, DataverseAddonTestCase, create_external_account,
)
from website.oauth.models import ExternalAccount


class TestDataverseViewsAuth(DataverseAddonTestCase):

    def test_deauthorize(self):
        url = api_url_for('dataverse_remove_user_auth',
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

    def test_user_config_get(self):
        url = api_url_for('dataverse_user_config_get')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_false(result['userHasAuth'])
        assert_in('hosts', result)
        assert_in('create', result['urls'])

        # userHasAuth is true with external accounts
        self.user.external_accounts.append(create_external_account())
        self.user.save()
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_true(result['userHasAuth'])


class TestDataverseViewsConfig(DataverseAddonTestCase):

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

    def test_dataverse_get_user_accounts(self):
        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.user.external_accounts.append(create_external_account())
        self.user.save()

        url = api_url_for('dataverse_get_user_accounts')
        res = self.app.get(url, auth=self.user.auth)
        accounts = res.json['accounts']

        assert_equal(len(accounts), 2)
        serializer = DataverseSerializer(user_settings=self.user_settings)
        assert_equal(
            accounts[0], serializer.serialize_account(external_account),
        )

    def test_dataverse_get_user_accounts_no_accounts(self):
        url = api_url_for('dataverse_get_user_accounts')
        res = self.app.get(url, auth=self.user.auth)
        accounts = res.json['accounts']

        assert_equal(len(accounts), 0)

    @mock.patch('website.addons.dataverse.views.config.client._connect')
    def test_dataverse_add_external_account(self, mock_connection):
        mock_connection.return_value = create_mock_connection()
        host = 'myfakehost.data.verse'
        token = 'api-token-here'

        url = api_url_for('dataverse_add_user_account')
        params = {'host': host, 'api_token': token}
        self.app.post_json(url, params, auth=self.user.auth)
        self.user.reload()

        assert_equal(len(self.user.external_accounts), 1)
        external_account = self.user.external_accounts[0]
        assert_equal(external_account.provider, 'dataverse')
        assert_equal(external_account.oauth_key, host)
        assert_equal(external_account.oauth_secret, token)

    @mock.patch('website.addons.dataverse.views.config.client._connect')
    def test_dataverse_add_external_account_fail(self, mock_connection):
        mock_connection.side_effect = UnauthorizedError('Bad credentials!')
        host = 'myfakehost.data.verse'
        token = 'api-token-here'

        url = api_url_for('dataverse_add_user_account')
        params = {'host': host, 'api_token': token}
        res = self.app.post_json(
            url, params, auth=self.user.auth, expect_errors=True,
        )
        self.user.reload()

        assert_equal(len(self.user.external_accounts), 0)
        assert_equal(res.status_code, http.UNAUTHORIZED)

    @mock.patch('website.addons.dataverse.views.config.client._connect')
    def test_dataverse_add_external_account_twice(self, mock_connection):
        mock_connection.return_value = create_mock_connection()
        host = 'myfakehost.data.verse'
        token = 'api-token-here'

        url = api_url_for('dataverse_add_user_account')
        params = {'host': host, 'api_token': token}
        self.app.post_json(url, params, auth=self.user.auth)
        self.app.post_json(url, params, auth=self.user.auth)
        self.user.reload()

        assert_equal(len(self.user.external_accounts), 1)
        external_account = self.user.external_accounts[0]
        assert_equal(external_account.provider, 'dataverse')
        assert_equal(external_account.oauth_key, host)
        assert_equal(external_account.oauth_secret, token)

    @mock.patch('website.addons.dataverse.views.config.client._connect')
    def test_dataverse_add_external_account_existing(self, mock_connection):
        mock_connection.return_value = create_mock_connection()
        host = 'myfakehost.data.verse'
        token = 'dont-use-this-token-in-other-tests'
        display_name = 'loaded_version'

        # Save an existing version
        external_account = ExternalAccount(
            provider='dataverse',
            provider_name='Dataverse',
            display_name=display_name,
            oauth_key=host,
            oauth_secret=token,
            provider_id=token,
        )
        external_account.save()

        url = api_url_for('dataverse_add_user_account')
        params = {'host': host, 'api_token': token}
        self.app.post_json(url, params, auth=self.user.auth)
        self.user.reload()

        assert_equal(len(self.user.external_accounts), 1)
        external_account = self.user.external_accounts[0]
        assert_equal(external_account.provider, 'dataverse')
        assert_equal(external_account.oauth_key, host)
        assert_equal(external_account.oauth_secret, token)
        # Ensure we got the loaded version
        assert_equal(external_account.display_name, display_name)

    @mock.patch('website.addons.dataverse.views.config.client.connect_from_settings')
    def test_set_dataverse_and_dataset(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_set_config',
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

        alias = self.node_settings.dataverse_alias
        doi = self.node_settings.dataset_doi
        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.user.save()
        self.node_settings.set_auth(external_account, self.user)
        self.node_settings.dataverse_alias = alias
        self.node_settings.dataset_doi = doi
        self.node_settings.save()

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

        alias = self.node_settings.dataverse_alias
        doi = self.node_settings.dataset_doi
        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.user.save()
        self.node_settings.set_auth(external_account, self.user)
        self.node_settings.dataverse_alias = alias
        self.node_settings.dataset_doi = doi
        self.node_settings.save()

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
    @mock.patch('website.addons.dataverse.views.crud.publish_dataverse')
    def test_dataverse_publish_dataset(self, mock_publish_dv, mock_publish_ds, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_publish_dataset',
                          pid=self.project._primary_key)
        self.app.put_json(url, params={'publish_both': False}, auth=self.user.auth)

        # Only dataset was published
        assert_false(mock_publish_dv.called)
        assert_true(mock_publish_ds.called)

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_401')
    @mock.patch('website.addons.dataverse.views.crud.publish_dataset')
    @mock.patch('website.addons.dataverse.views.crud.publish_dataverse')
    def test_dataverse_publish_both(self, mock_publish_dv, mock_publish_ds, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_publish_dataset',
                          pid=self.project._primary_key)
        self.app.put_json(url, params={'publish_both': True}, auth=self.user.auth)

        # Both Dataverse and dataset were published
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

        url = api_url_for('dataverse_set_config', pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS1'},
            'dataset': {'doi': 'doi:12.3456/DVN/00002'},
        }
        res = self.app.post_json(url, params, auth=self.contrib.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)


if __name__ == '__main__':
    nose.run()
