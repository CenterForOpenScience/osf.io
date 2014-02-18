import mock
from nose.tools import *
from webtest_plus import TestApp

import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class TestS3ViewsConfig(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()
        self.node_url = '/api/v1/project/{0}/'.format(self.project._id)

    @mock.patch('website.addons.s3.views.config.does_bucket_exist')
    @mock.patch('website.addons.s3.views.config.adjust_cors')
    def test_s3_settings_no_bucket(self, mock_cors, mock_does_bucket_exist):
        mock_does_bucket_exist.return_value = False
        mock_cors.return_value = True
        url = "/api/v1/project/{0}/s3/settings/".format(self.project._id)
        rv = self.app.post_json(url, {}, expect_errors=True, auth=self.user.auth)
        assert_true('trouble' in rv.body)

    @mock.patch('website.addons.s3.views.config.remove_osf_user')
    def test_s3_remove_user_settings(self, mock_access):
        mock_access.return_value = True
        self.user_settings.access_key = 'to-kill-a-mocking-bucket'
        self.user_settings.secret_key = 'itsasecret'
        self.user_settings.save()
        url = '/api/v1/settings/s3/'
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, '')
        assert_equals(self.user_settings.secret_key, '')

    def test_download_no_file(self):
        url = "/api/v1/project/{0}/s3/download/".format(self.project._id)
        self.app.post_json(url, {},  expect_errors=True)

    @mock.patch('website.addons.s3.views.config.has_access')
    def test_user_settings_no_auth(self, mock_access):
        mock_access.return_value = False
        url = '/api/v1/settings/s3/'
        rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, 400)

    @mock.patch('website.addons.s3.views.config.has_access')
    @mock.patch('website.addons.s3.views.config.create_osf_user')
    def test_user_settings(self, mock_user, mock_access):
        mock_access.return_value = True
        mock_user.return_value = {
            'access_key_id': 'scout',
            'secret_access_key': 'ssshhhhhhhhh'
        }
        url = '/api/v1/settings/s3/'
        self.app.post_json(
            url,
            {
                'access_key': 'scout',
                'secret_key': 'Aticus'
            },
            auth=self.user.auth
        )
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    @mock.patch('website.addons.s3.views.config.has_access')
    @mock.patch('website.addons.s3.views.config.create_osf_user')
    def test_node_settings_no_user_settings(self, mock_user, mock_access):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = self.node_url + 's3/authorize/'

        mock_access.return_value = True
        mock_user.return_value = {
            'access_key_id': 'scout',
            'secret_access_key': 'ssshhhhhhhhh'
        }
        self.app.post_json(url, {'access_key': 'scout', 'secret_key': 'ssshhhhhhhhh'}, auth=self.user.auth)

        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    def test_node_settings_no_user_settings_ui(self):
        self.node_settings.user_settings.access_key = None
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = '/' + self.project._id + '/settings/'
        rv = self.app.get(url, auth=self.user.auth)
        assert_true('<label for="s3Addon">Access Key</label>' in rv.body)

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_user_settings_ui(self, dropdown):
        dropdown.return_value = 'test'
        url = '/' + self.project._id + '/settings/'
        rv = self.app.get(url, auth=self.user.auth)
        assert_true('Your buckets' in rv.body)


class TestS3ViewsCRUD(DbTestCase):
    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()
        self.node_url =  '/api/v1/project/{0}/'.format(self.project._id)

    def test_view_no_file(self):
        url = '/project/{0}/s3/view/'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, 404)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_view_faux_file(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.get_wrapped_key.return_value = None
        url = '/project/{0}/s3/view/faux.sho/'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, 404)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_view_upload_url(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.does_key_exist.return_value = False
        rv = self.app.post_json(self.node_url + 's3/upload/', {'name': 'faux.sho'}, auth=self.user.auth)
        assert_true('faux.sho' in rv.body and self.node_settings.bucket in rv.body and rv.status_int == 200)

    def test_download_file_no_file(self):
        rv = self.app.post_json(self.node_url + 's3/download/', {}, expect_errors=True)
        assert_equals(rv.status_int, 404)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_download_file_faux_file(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.does_key_exist.return_value = False
        rv = self.app.post_json(self.node_url + 's3/download/', {'path': 'faux.show'}, expect_errors=True)
        assert_equals(rv.status_int, 404)


class TestS3ViewsHgrid(DbTestCase):
    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()
        #self.app.authenticate(*self.user.auth)

    def test_data_contents_no_user_settings(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = "/api/v1/project/{0}/s3/hgrid/".format(self.project._id)
        rv = self.app.get(url, expect_errors=True, auth=self.user.auth)
        assert_equals(rv.status_int, 400)

    def test_dummy_folder(self):
        url = "/api/v1/project/{0}/s3/hgrid/dummy/".format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth)
        assert_true(self.node_settings.bucket in rv.body)

    def test_dummy_folder_no_user_settings(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = "/api/v1/project/{0}/s3/hgrid/dummy/".format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth)
        assert_equals(rv.body, 'null')

    def test_dummy_folder_no_bucket(self):
        self.node_settings.bucket = None
        self.node_settings.save()
        url = "/api/v1/project/{0}/s3/hgrid/dummy/".format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth)
        assert_equals(rv.body, 'null')
