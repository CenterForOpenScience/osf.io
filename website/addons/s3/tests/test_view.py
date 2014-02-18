import mock
from nose.tools import *
from webtest.app import AppError
from webtest_plus import TestApp

import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.s3.model import AddonS3NodeSettings, S3GuidFile

from utils import create_mock_wrapper, create_mock_key

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class TestS3Views(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')
        self.user_settings = self.user.get_addon('s3')
        self.node_settings = self.project.get_addon('s3')
        # Set the node addon settings to correspond to the values of the mock
        # repo
        self.node_settings = AddonS3NodeSettings()
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()
        self.user_settings.save()
        self.app.authenticate(*self.user.auth)

    @mock.patch('website.addons.s3.views.config.does_bucket_exist')
    @mock.patch('website.addons.s3.views.config.adjust_cors')
    def test_s3_settings_no_bucket(self, mock_cors, mock_does_bucket_exist):
        mock_does_bucket_exist.return_value = False
        mock_cors.return_value = True
        url = "/api/v1/project/{0}/s3/settings/".format(self.project._id)
        self.app.post_json(url, {}, expect_errors=True)

    @mock.patch('website.addons.s3.views.config.remove_osf_user')
    def test_s3_remove_user_settings(self, mock_access):
        mock_access.return_value = True
        self.user_settings.access_key = 'to-kill-a-mocking-bucket'
        self.user_settings.secret_key = 'itsasecret'
        self.user_settings.save()
        url = '/api/v1/settings/s3/'
        self.app.delete_json(url, {}, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, '')
        # TODO finish me

    def test_download_no_file(self):
        url = "/api/v1/project/{0}/s3/download/".format(self.project._id)
        self.app.post_json(url, {},  expect_errors=True)

    # TODO fix me cant seem to be logged in.....
    @mock.patch('website.addons.s3.views.config.has_access')
    def test_user_settings_no_auth(self, mock_access):
        mock_access.return_value = False
        url = '/api/v1/settings/s3/'
        with assert_raises(AppError):
            self.app.post_json(url, {})

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
            }
        )
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    @mock.patch('website.addons.s3.api.S3Wrapper.get_wrapped_key')
    @mock.patch('website.addons.s3.api.S3Wrapper.from_addon')
    def test_view_creates_guid(self, mock_from_addon, mock_wrapped_key):

        mock_from_addon.return_value = create_mock_wrapper()
        mock_wrapped_key.return_value = create_mock_key()

        guid_count = S3GuidFile.find().count()

        # View file for the first time
        url = self.project.url + 's3/test.py'
        res = self.app.get(url, auth=self.user.auth).maybe_follow(auth=self.user.auth)

        guids = S3GuidFile.find()

        # GUID count has been incremented by one
        assert_equal(
            guids.count(),
            guid_count + 1
        )

        # Client has been redirected to GUID
        assert_equal(
            res.request.path.strip('/'),
            guids[guids.count() - 1]._id
        )

        # View file for the second time
        self.app.get(url, auth=self.user.auth).maybe_follow()

        # GUID count has not been incremented
        assert_equal(
            S3GuidFile.find().count(),
            guid_count + 1
        )
