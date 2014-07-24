import nose
from nose.tools import *
import mock
import json

import httplib as http
from tests.factories import AuthUserFactory
from framework.auth.decorators import Auth
from framework.exceptions import HTTPError
from webtest import Upload
from website.util import api_url_for, web_url_for
from website.addons.dataverse.settings import HOST
from website.addons.dataverse.views.config import serialize_settings
from website.addons.dataverse.views.crud import fail_if_unauthorized
from website.addons.dataverse.tests.utils import create_mock_connection, \
    create_mock_draft_file, DataverseAddonTestCase, mock_responses, \
    create_mock_study


class TestDataverseViewsAuth(DataverseAddonTestCase):

    def test_deauthorize(self):
        url = api_url_for('deauthorize_dataverse',
                          pid=self.project._primary_key)
        self.app.delete(url, auth=self.user.auth)

        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
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
        assert_true(self.user_settings.dataverse_username)
        assert_true(self.user_settings.dataverse_password)

        # Aurthoized user can delete
        self.app.delete_json(url, auth=self.user.auth)

        # User is no longer authorized
        self.user_settings.reload()
        assert_false(self.user_settings.dataverse_username)
        assert_false(self.user_settings.dataverse_password)

        # User's authorized nodes are now deauthorized
        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user_settings)

    @mock.patch('website.addons.dataverse.views.auth.connect_from_settings_or_403')
    def test_user_config_get(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_user_config_get')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_true(result['connected'])
        assert_true(result['userHasAuth'])
        assert_equal(result['dataverseUsername'],
                     self.user_settings.dataverse_username)
        assert_in('create', result['urls'])
        assert_in('delete', result['urls'])

    @mock.patch('website.addons.dataverse.views.auth.connect_from_settings_or_403')
    def test_user_config_get_no_connection(self, mock_connection):
        mock_connection.return_value = None

        url = api_url_for('dataverse_user_config_get')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_false(result['connected'])
        assert_true(result['userHasAuth'])
        assert_equal(result['dataverseUsername'],
                     self.user_settings.dataverse_username)
        assert_in('create', result['urls'])
        assert_in('delete', result['urls'])


class TestDataverseViewsConfig(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_serialize_settings_helper_returns_correct_auth_info(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = serialize_settings(self.node_settings, self.user)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
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
        stranger_settings.dataverse_username = 'foo'
        stranger_settings.dataverse_password = 'bar'
        stranger_settings.save()
        result = serialize_settings(self.node_settings, stranger)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_false(result['userIsOwner'])

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_serialize_settings_helper_returns_correct_urls(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = serialize_settings(self.node_settings, self.user)
        urls = result['urls']

        assert_equal(urls['set'], self.project.api_url_for('set_dataverse_and_study'))
        assert_equal(urls['importAuth'], self.project.api_url_for('dataverse_import_user_auth'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('deauthorize_dataverse'))
        assert_equal(urls['getStudies'], self.project.api_url_for('dataverse_get_studies'))
        assert_equal(urls['studyPrefix'], 'http://dx.doi.org/')
        assert_equal(urls['dataversePrefix'], 'http://{0}/dvn/dv/'.format(HOST))
        assert_equal(urls['owner'], web_url_for('profile_view_id', uid=self.user._primary_key))

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_serialize_settings_helper_returns_dv_info(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        result = serialize_settings(self.node_settings, self.user)

        assert_equal(len(result['dataverses']), 3)
        assert_equal(result['savedDataverse']['title'], self.node_settings.dataverse)
        assert_equal(result['savedDataverse']['alias'], self.node_settings.dataverse_alias)
        assert_equal(result['savedStudy']['title'], self.node_settings.study)
        assert_equal(result['savedStudy']['hdl'], self.node_settings.study_hdl)

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_serialize_settings_helper_no_connection(self, mock_connection):
        mock_connection.return_value = None

        result = serialize_settings(self.node_settings, self.user)

        assert_false(result['dataverses'])
        assert_equal(result['savedDataverse']['title'], self.node_settings.dataverse)
        assert_equal(result['savedDataverse']['alias'], self.node_settings.dataverse_alias)
        assert_equal(result['savedStudy']['title'], self.node_settings.study)
        assert_equal(result['savedStudy']['hdl'], self.node_settings.study_hdl)

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_dataverse_get_studies(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_get_studies', pid=self.project._primary_key)
        params = {'alias': 'ALIAS1'}
        res = self.app.post_json(url, params, auth=self.user.auth)

        assert_equal(len(res.json['studies']), 3)
        first = res.json['studies'][0]
        assert_equal(first['title'], 'Example (DVN/00001)')
        assert_equal(first['hdl'], 'doi:12.3456/DVN/00001')

    @mock.patch('website.addons.dataverse.views.config.connect')
    def test_set_user_config(self, mock_connection):

        mock_connection.return_value = create_mock_connection()

        # Create a user with no settings
        user = AuthUserFactory()
        user.add_addon('dataverse')
        user_settings = user.get_addon('dataverse')

        url = api_url_for('dataverse_set_user_config')
        params = {'dataverse_username': 'snowman',
                  'dataverse_password': 'frosty'}

        # Post dataverse credentials
        self.app.post_json(url, params, auth=user.auth)
        user_settings.reload()

        # User settings have updated correctly
        assert_equal(user_settings.dataverse_username, 'snowman')
        assert_equal(user_settings.dataverse_password, 'frosty')

    @mock.patch('website.addons.dataverse.views.config.connect')
    def test_set_user_config_fail(self, mock_connection):

        mock_connection.return_value = create_mock_connection('wrong', 'info')

        # Create a user with no settings
        user = AuthUserFactory()
        user.add_addon('dataverse')
        user_settings = user.get_addon('dataverse')

        url = api_url_for('dataverse_set_user_config')
        params = {'dataverse_username': 'wrong',
                  'dataverse_password': 'info'}

        # Post incorrect credentials to existing user
        res = self.app.post_json(url, params, auth=self.user.auth,
                                 expect_errors=True)
        self.user_settings.reload()

        # Original user's info has not changed
        assert_equal(res.status_code, http.UNAUTHORIZED)
        assert_equal(self.user_settings.dataverse_username, 'snowman')
        assert_equal(self.user_settings.dataverse_password, 'frosty')

        # Post incorrect credentials to new user
        res = self.app.post_json(url, params, auth=user.auth,
                                 expect_errors=True)
        user_settings.reload()

        # New user's incorrect credentials were not saved
        assert_equal(res.status_code, http.UNAUTHORIZED)
        assert_equal(user_settings.dataverse_username, None)
        assert_equal(user_settings.dataverse_password, None)

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_set_dataverse_and_study(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('set_dataverse_and_study',
                          pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS3'},
            'study': {'hdl': 'doi:12.3456/DVN/00003'},
        }

        # Select a different study
        self.app.post_json(url, params, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        # New study was selected
        assert_equal(self.node_settings.dataverse_alias, 'ALIAS3')
        assert_equal(self.node_settings.study, 'Example (DVN/00003)')
        assert_equal(self.node_settings.study_hdl, 'doi:12.3456/DVN/00003')

        # Log states that a study was selected
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dataverse_study_linked')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_is_none(log_params['project'])
        assert_equal(log_params['study'], 'Example (DVN/00003)')

    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_set_dataverse_no_study(self, mock_connection):
        mock_connection.return_value = create_mock_connection()
        num_old_logs = len(self.project.logs)

        url = api_url_for('set_dataverse_and_study',
                          pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS3'},
            'study': {},    # The dataverse has no studies
        }

        # Select a different study
        res = self.app.post_json(url, params, auth=self.user.auth,
                                 expect_errors=True)
        self.node_settings.reload()

        # Old settings did not change
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(self.node_settings.dataverse_alias, 'ALIAS2')
        assert_equal(self.node_settings.study, 'Example (DVN/00001)')
        assert_equal(self.node_settings.study_hdl, 'doi:12.3456/DVN/00001')

        # Nothing was logged
        self.project.reload()
        assert_equal(len(self.project.logs), num_old_logs)


class TestDataverseViewsHgrid(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    @mock.patch('website.addons.dataverse.views.hgrid.get_study')
    def test_dataverse_data_contents(self, mock_get, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'
        mock_get.return_value = create_mock_study()

        url = api_url_for('dataverse_hgrid_data_contents',
                          pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        contents = mock_responses['contents']
        first = res.json['data'][0]
        assert_equal(mock_get.call_args[0][1], self.node_settings.study_hdl)
        assert_equal(len(first), len(contents))
        assert_in('kind', first)
        assert_equal(first['name'], contents['name'])

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    def test_dataverse_data_contents_no_connection(self, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'

        # If there is no connection, no files are returned
        mock_connection.return_value = None
        url = api_url_for('dataverse_hgrid_data_contents',
                          pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    def test_dataverse_data_contents_no_study(self, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'

        # If there is no study, no data are returned
        self.node_settings.study_hdl = None
        self.node_settings.save()
        url = api_url_for('dataverse_hgrid_data_contents',
                          pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    def test_dataverse_data_contents_state_on_file_page(self, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_hgrid_data_contents',
                          pid=self.project._primary_key)

        # Creator posts, gets draft version
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['name'], 'file.txt')

        # Noncontributor posts, gets released version
        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_equal(res.json['data'][0]['name'], 'released.txt')

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    def test_dataverse_data_contents_state_on_dashboard(self, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/'
        mock_request.args = {}

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_hgrid_data_contents',
                          pid=self.project._primary_key)

        # All users get released version
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['name'], 'released.txt')

        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_equal(res.json['data'][0]['name'], 'released.txt')

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_released(self, mock_files, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'
        mock_request.args = {'state': 'released'}
        mock_files.return_value = ['mock_file']

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_root_folder_public',
                          pid=self.project._primary_key)

        # Contributor can select between states, current state is correct
        res = self.app.get(url, auth=self.user.auth)
        assert_in('released', res.json[0]['urls']['fetch'])
        assert_false(res.json[0]['permissions']['edit'])
        assert_in('<option value="released" selected>', res.json[0]['extra'])

        # Non-contributor gets released version, no options
        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_in('released', res.json[0]['urls']['fetch'])
        assert_false(res.json[0]['permissions']['edit'])
        assert_not_in('select', res.json[0]['extra'])

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_draft(self, mock_files, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'
        mock_request.args = {'state': 'draft'}
        mock_files.return_value = ['mock_file']

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_root_folder_public',
                          pid=self.project._primary_key)

        # Contributor can select between states, current state is correct
        res = self.app.get(url, auth=self.user.auth)
        assert_in('draft', res.json[0]['urls']['fetch'])
        assert_true(res.json[0]['permissions']['edit'])
        assert_in('<option value="draft" selected>', res.json[0]['extra'])

        # Non-contributor gets released version, no options
        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_in('released', res.json[0]['urls']['fetch'])
        assert_false(res.json[0]['permissions']['edit'])
        assert_not_in('select', res.json[0]['extra'])

    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_not_released(self, mock_files, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'
        mock_request.args = {'state': 'released'}
        mock_files.return_value = []

        self.project.set_privacy('public')
        self.project.save()

        url = api_url_for('dataverse_root_folder_public',
                          pid=self.project._primary_key)

        # Contributor gets draft, no options
        res = self.app.get(url, auth=self.user.auth)
        assert_in('draft', res.json[0]['urls']['fetch'])
        assert_true(res.json[0]['permissions']['edit'])
        assert_not_in('select', res.json[0]['extra'])

        # Non-contributor gets nothing
        user2 = AuthUserFactory()
        res = self.app.get(url, auth=user2.auth)
        assert_equal(res.json, [])


    @mock.patch('website.addons.dataverse.views.hgrid.connect_from_settings')
    @mock.patch('website.addons.dataverse.views.hgrid.request')
    @mock.patch('website.addons.dataverse.views.hgrid.get_files')
    def test_dataverse_root_no_connection(self, mock_files, mock_request, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_request.referrer = 'some_url/files/'
        mock_request.args = {'state': 'released'}
        mock_files.return_value = ['mock_file']

        url = api_url_for('dataverse_root_folder_public',
                          pid=self.project._primary_key)

        mock_connection.return_value = None
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json, [])


class TestDataverseViewsCrud(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.delete_file')
    @mock.patch('website.addons.dataverse.views.crud.get_file_by_id',
                side_effect=[create_mock_draft_file('54321'), None])
    def test_delete_file(self, mock_get, mock_delete, mock_connection):
        mock_get.return_value = None
        mock_connection.return_value = create_mock_connection()

        path = '54321'
        url = api_url_for('dataverse_delete_file',
                          pid=self.project._primary_key, path=path)

        res = self.app.delete(url=url, auth=self.user.auth)

        mock_delete.assert_called_once
        assert_equal(path, mock_delete.call_args[0][0].id)

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.upload_file')
    @mock.patch('website.addons.dataverse.views.crud.get_file',
                side_effect=[None, create_mock_draft_file()])
    def test_upload_file(self, mock_get, mock_upload, mock_connection):
        mock_upload.return_value = {}
        mock_connection.return_value = create_mock_connection()

        # Define payload
        filename = 'myfile.rst'
        content = 'bazbaz'
        path = '54321'
        payload = {'file': Upload(filename, content,'text/x-rst')}

        # Upload the file
        url = api_url_for('dataverse_upload_file',
                          pid=self.project._primary_key, path=path)
        res = self.app.post(url, payload, auth=self.user.auth)

        # File was uploaded
        assert_equal(res.status_code, http.CREATED)
        mock_upload.assert_called_once

        # Parameters are correct
        assert_equal(self.node_settings.study_hdl,
                     mock_upload.call_args[0][0].doi)
        assert_equal(filename, mock_upload.call_args[0][1])
        assert_equal(content, mock_upload.call_args[0][2])
        assert_equal('file_uploaded', json.loads(res.body)['actionTaken'])

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.upload_file')
    @mock.patch('website.addons.dataverse.views.crud.delete_file')
    @mock.patch('website.addons.dataverse.views.crud.get_file')
    @mock.patch('website.addons.dataverse.views.crud.get_file_by_id')
    def test_upload_existing(self, mock_get_by_id, mock_get, mock_delete,
                             mock_upload, mock_connection):
        mock_get.return_value = create_mock_draft_file()  # File already exists
        mock_get_by_id.return_value = None  # To confirm deletion happened
        mock_upload.return_value = {}
        mock_connection.return_value = create_mock_connection()

        # Define payload
        filename = 'myfile.rst'
        content = 'bazbaz'
        path = '54321'
        payload = {'file': Upload(filename, content,'text/x-rst')}

        # Attempt to upload the file
        url = api_url_for('dataverse_upload_file',
                          pid=self.project._primary_key, path=path)
        res = self.app.post(url, payload, auth=self.user.auth)

        # Old file was deleted
        mock_delete.assert_called_once

        # File was uploaded
        assert_equal(res.status_code, http.CREATED)
        mock_upload.assert_called_once

        # Parameters are correct
        assert_equal(self.node_settings.study_hdl,
                     mock_upload.call_args[0][0].doi)
        assert_equal(filename, mock_upload.call_args[0][1])
        assert_equal(content, mock_upload.call_args[0][2])
        assert_equal('file_updated', json.loads(res.body)['actionTaken'])

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.upload_file')
    @mock.patch('website.addons.dataverse.views.crud.delete_file')
    @mock.patch('website.addons.dataverse.views.crud.get_file')
    def test_upload_too_small(self, mock_get, mock_delete, mock_upload,
                             mock_connection):
        mock_get.return_value = create_mock_draft_file() # File already exists
        mock_upload.return_value = {}
        mock_connection.return_value = create_mock_connection()

        # Define payload
        filename = 'myfile.rst'
        content = 'baz'
        path = '54321'
        payload = {'file': Upload(filename, content,'text/x-rst')}

        # Attempt to upload the file
        url = api_url_for('dataverse_upload_file',
                          pid=self.project._primary_key, path=path)
        res = self.app.post(url, payload, auth=self.user.auth,
                            expect_errors=True)

        # Old file was not deleted
        assert_false(mock_delete.call_count)

        # Bad request
        assert_equal(res.status_code, http.UNSUPPORTED_MEDIA_TYPE)
        assert_false(mock_upload.call_count)

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.get_files')
    def test_dataverse_view_file(self, mock_get_files, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_get_files.return_value = [create_mock_draft_file('foo')]

        url = web_url_for('dataverse_view_file',
                          pid=self.project._primary_key, path='foo')
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.get_files')
    def test_download_file(self, mock_get_files, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_get_files.return_value = [create_mock_draft_file('foo')]

        path = 'foo'
        url = web_url_for('dataverse_download_file',
                          pid=self.project._primary_key, path=path)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(
            res.headers.get('location'),
            'http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, path),
        )

    @mock.patch('website.addons.dataverse.views.crud.connect_from_settings_or_403')
    @mock.patch('website.addons.dataverse.views.crud.release_study')
    def test_dataverse_release_study(self, mock_release, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = api_url_for('dataverse_release_study',
                          pid=self.project._primary_key)
        res = self.app.put(url, auth=self.user.auth)
        assert_true(mock_release.called)

    @mock.patch('website.addons.dataverse.views.crud.get_cache_content')
    def test_render_file(self, mock_get_cache):
        mock_get_cache.return_value = 'Mockument (A mock document)'

        file_id = '23456'

        url = api_url_for('dataverse_get_rendered_file',
                          pid=self.project._primary_key, path=file_id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(mock_get_cache.call_args[0][1],
                     '{0}.html'.format(file_id))

    def test_fail_if_unauthorized_not_found(self):

        with assert_raises(HTTPError) as error:
            fail_if_unauthorized(self.node_settings, self.user.auth, None)
            assert_equal(error.code, http.NOT_FOUND)

    @mock.patch('website.addons.dataverse.views.crud.get_files')
    def test_fail_if_unauthorized_forbidden(self, mock_get_files):
        mock_get_files.return_value = [create_mock_draft_file('foo')]
        with assert_raises(HTTPError) as error:
            fail_if_unauthorized(self.node_settings, self.user.auth, 'bar')
            assert_equal(error.code, http.FORBIDDEN)

    @mock.patch('website.addons.dataverse.views.crud.get_files',
                side_effect=[[create_mock_draft_file('released')],
                             [create_mock_draft_file('draft')]])
    def test_fail_if_unauthorized_unauthorized(self, mock_get_files):
        with assert_raises(HTTPError) as error:
            user2 = AuthUserFactory()
            fail_if_unauthorized(self.node_settings, Auth(user2), 'draft')
            assert_equal(error.code, http.UNAUTHORIZED)


class TestDataverseRestrictions(DataverseAddonTestCase):

    def setUp(self):
        super(DataverseAddonTestCase, self).setUp()

        # Nasty contributor who will try to access content that he shouldn't
        # have access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()


    @mock.patch('website.addons.dataverse.views.config.connect_from_settings')
    def test_restricted_set_study_not_owner(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        # Contributor has dataverse auth, but is not the node authorizer
        self.contrib.add_addon('dataverse')
        self.contrib.save()

        url = api_url_for('set_dataverse_and_study', pid=self.project._primary_key)
        params = {
            'dataverse': {'alias': 'ALIAS1'},
            'study': {'hdl': 'doi:12.3456/DVN/00002'},
        }
        res = self.app.post_json(url, params, auth=self.contrib.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)


if __name__=='__main__':
    nose.run()