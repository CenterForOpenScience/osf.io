import nose
from nose.tools import *
import mock
from webtest_plus import TestApp

import httplib as http
from framework.auth.decorators import Auth
import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.dataverse.views.crud import scrape_dataverse

from utils import create_mock_connection

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class TestDataverseViewsAuth(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('dataverse', auth=self.consolidated_auth)
        self.user.add_addon('dataverse')

        self.user_settings = self.user.get_addon('dataverse')
        self.user_settings.dataverse_username = 'snowman'
        self.user_settings.dataverse_password = 'frosty'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('dataverse')
        self.node_settings.user_settings = self.project.creator.get_addon('dataverse')
        self.node_settings.dataverse_username = self.user_settings.dataverse_username
        self.node_settings.dataverse_password = self.user_settings.dataverse_password
        self.node_settings.dataverse_number = 1
        self.node_settings.dataverse = 'Example 2'
        self.node_settings.study_hdl = 'DVN/00001'
        self.node_settings.study = 'Example (DVN/00001)'
        self.node_settings.user = self.user
        self.node_settings.save()

    @mock.patch('website.addons.dataverse.views.auth.connect')
    def test_authorize(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = self.project.api_url + 'dataverse/authorize/'
        self.app.post_json(url, auth=self.user.auth)

        self.node_settings.reload()

        assert_equal(self.node_settings.user, self.user)
        assert_equal(self.node_settings.user_settings, self.user_settings)
        assert_equal(self.node_settings.dataverse_username, 'snowman')
        assert_equal(self.node_settings.dataverse_password, 'frosty')

    @mock.patch('website.addons.dataverse.views.auth.connect')
    def test_authorize_fail(self, mock_connection):
        mock_connection.return_value = create_mock_connection('wrong', 'info')

        url = self.project.api_url + 'dataverse/authorize/'
        res = self.app.post_json(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_unauthorize(self):
        url = self.project.api_url + 'dataverse/unauthorize/'
        self.app.post_json(url, auth=self.user.auth)

        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_username)
        assert_false(self.node_settings.dataverse_password)
        assert_equal(self.node_settings.dataverse_number, 0)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user)

    def test_delete_user(self):
        url = '/api/v1/settings/dataverse/'

        # Non-authorized user can't delete
        user2 = AuthUserFactory()
        self.app.delete_json(url, auth=user2.auth, expect_errors=True)
        self.user_settings.reload()
        assert_true(self.user_settings.dataverse_username)

        # Aurthoized user can delete
        self.app.delete_json(url, auth=self.user.auth)

        # User is no longer authorized
        self.user_settings.reload()
        assert_false(self.user_settings.dataverse_username)
        assert_false(self.user_settings.dataverse_password)

        # User's authorized nodes are now unauthorized
        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_username)
        assert_false(self.node_settings.dataverse_password)
        assert_equal(self.node_settings.dataverse_number, 0)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user)


class TestDataverseViewsConfig(DbTestCase):
    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('dataverse', auth=self.consolidated_auth)
        self.user.add_addon('dataverse')

        self.user_settings = self.user.get_addon('dataverse')
        self.user_settings.dataverse_username = 'snowman'
        self.user_settings.dataverse_password = 'frosty'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('dataverse')
        self.node_settings.user_settings = self.project.creator.get_addon('dataverse')
        self.node_settings.dataverse_username = self.user_settings.dataverse_username
        self.node_settings.dataverse_password = self.user_settings.dataverse_password
        self.node_settings.dataverse_number = 1
        self.node_settings.dataverse = 'Example 2'
        self.node_settings.study_hdl = 'DVN/00001'
        self.node_settings.study = 'Example (DVN/00001)'
        self.node_settings.user = self.user
        self.node_settings.save()

    @mock.patch('website.addons.dataverse.views.config.connect')
    def test_set_user_config(self, mock_connection):

        mock_connection.return_value = create_mock_connection()

        # Create a user with no settings
        user = AuthUserFactory()
        user.add_addon('dataverse')
        user_settings = user.get_addon('dataverse')

        url = '/api/v1/settings/dataverse/'
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

        url = '/api/v1/settings/dataverse/'
        params = {'dataverse_username': 'wrong',
                  'dataverse_password': 'info'}

        # Post incorrect credentials to existing user
        res = self.app.post_json(url, params, auth=self.user.auth,
                                 expect_errors=True)
        self.user_settings.reload()

        # Original user's info has not changed
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(self.user_settings.dataverse_username, 'snowman')
        assert_equal(self.user_settings.dataverse_password, 'frosty')

        # Post incorrect credentials to new user
        res = self.app.post_json(url, params, auth=user.auth,
                                 expect_errors=True)
        user_settings.reload()

        # New user's incorrect credentials were not saved
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(user_settings.dataverse_username, None)
        assert_equal(user_settings.dataverse_password, None)

    @mock.patch('website.addons.dataverse.views.config.connect')
    def test_set_dataverse(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = self.project.api_url + 'dataverse/set/'
        params = {'dataverse_number': 0}

        self.app.post_json(url, params, auth=self.user.auth)
        self.node_settings.reload()

        assert_equal(self.node_settings.dataverse_number, 0)
        assert_equal(self.node_settings.dataverse, 'Example 1')
        assert_equal(self.node_settings.study, None)
        assert_equal(self.node_settings.study_hdl, None)

    @mock.patch('website.addons.dataverse.views.config.connect')
    def test_set_study(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = self.project.api_url + 'dataverse/set/study/'
        params = {'study_hdl': 'DVN/00001'}

        self.app.post_json(url, params, auth=self.user.auth)
        self.node_settings.reload()

        assert_equal(self.node_settings.dataverse_number, 1)
        assert_equal(self.node_settings.study, 'Example (DVN/00001)')
        assert_equal(self.node_settings.study_hdl, 'DVN/00001')

    @mock.patch('website.addons.dataverse.views.config.connect')
    def test_set_study_to_none(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        url = self.project.api_url + 'dataverse/set/study/'
        params = {'study_hdl': 'None'}

        self.app.post_json(url, params, auth=self.user.auth)
        self.node_settings.reload()

        assert_equal(self.node_settings.dataverse_number, 1)
        assert_equal(self.node_settings.study, None)
        assert_equal(self.node_settings.study_hdl, None)


def test_scrape_dataverse():
    content = scrape_dataverse(2362170)
    assert_not_in('IQSS', content)
    assert_in('%esp', content)

if __name__=='__main__':
    nose.run()