import mock
from nose.tools import *  # noqa

import httplib as http
from boto.exception import S3ResponseError

from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.s3.model import S3GuidFile

from website.addons.s3.utils import validate_bucket_name

from utils import create_mock_wrapper, create_mock_key


class TestS3ViewsConfig(OsfTestCase):

    def setUp(self):

        super(TestS3ViewsConfig, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3', auth=self.consolidated_auth)
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
        url = self.project.api_url + 's3/settings/'
        rv = self.app.post_json(url, {}, expect_errors=True, auth=self.user.auth)
        assert_true('trouble' in rv.body)

    @mock.patch('website.addons.s3.views.config.does_bucket_exist')
    @mock.patch('website.addons.s3.views.config.adjust_cors')
    def test_s3_set_bucket(self, mock_cors, mock_exist):

        mock_cors.return_value = True
        mock_exist.return_value = True

        url = self.project.api_url + 's3/settings/'
        self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=self.user.auth,
        )

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.bucket, 'hammertofall')
        assert_equal(self.project.logs[-1].action, 's3_bucket_linked')

    def test_s3_set_bucket_no_settings(self):

        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_s3_set_bucket_no_auth(self):

        user = AuthUserFactory()
        user.add_addon('s3')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_s3_set_bucket_already_authed(self):

        user = AuthUserFactory()
        user.add_addon('s3')
        user_settings = user.get_addon('s3')
        user_settings.access_key = 'foo'
        user_settings.secret_key = 'bar'
        user_settings.save()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('website.addons.s3.api.S3Wrapper.get_wrapped_key')
    @mock.patch('website.addons.s3.api.S3Wrapper.from_addon')
    def test_s3_set_bucket_registered(self, mock_from_addon, mock_wrapped_key):

        mock_from_addon.return_value = create_mock_wrapper()
        mock_wrapped_key.return_value = create_mock_key()

        registration = self.project.register_node(
            None, self.consolidated_auth, '', ''
        )

        url = registration.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=self.user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('website.addons.s3.views.config.has_access')
    @mock.patch('website.addons.s3.views.config.create_osf_user')
    def test_user_settings(self, mock_user, mock_access):
        mock_access.return_value = True
        mock_user.return_value = (
            'osf-user-12345',
            {
                'access_key_id': 'scout',
                'secret_access_key': 'ssshhhhhhhhh'
            }
        )
        url = '/api/v1/settings/s3/'
        self.app.post_json(
            url,
            {
                'access_key': 'scout',
                'secret_key': 'Atticus'
            },
            auth=self.user.auth
        )
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.remove_iam_user')
    def test_s3_remove_user_settings(self, mock_access):
        mock_access.return_value = True
        self.user_settings.access_key = 'to-kill-a-mocking-bucket'
        self.user_settings.secret_key = 'itsasecret'
        self.user_settings.save()
        url = '/api/v1/settings/s3/'
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, None)
        assert_equals(self.user_settings.secret_key, None)
        assert_equals(mock_access.call_count, 1)

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.remove_iam_user')
    def test_s3_remove_user_settings_none(self, mock_access):
        self.user_settings.access_key = None
        self.user_settings.secret_key = None
        self.user_settings.save()
        url = '/api/v1/settings/s3/'
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(mock_access.call_count, 0)

    @mock.patch('website.addons.s3.views.config.has_access')
    def test_user_settings_no_auth(self, mock_access):
        mock_access.return_value = False
        url = '/api/v1/settings/s3/'
        rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)

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
        self.app.get(url, auth=self.user.auth).follow(auth=self.user.auth)

        # GUID count has not been incremented
        assert_equal(
            S3GuidFile.find().count(),
            guid_count + 1
        )

    @mock.patch('website.addons.s3.views.config.has_access')
    @mock.patch('website.addons.s3.views.config.create_osf_user')
    def test_node_settings_no_user_settings(self, mock_user, mock_access):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = self.node_url + 's3/authorize/'

        mock_access.return_value = True
        mock_user.return_value = (
            'osf-user-12345',
            {
                'access_key_id': 'scout',
                'secret_access_key': 'ssshhhhhhhhh'
            }
        )
        self.app.post_json(url, {'access_key': 'scout', 'secret_key': 'ssshhhhhhhhh'}, auth=self.user.auth)

        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    def test_node_settings_no_user_settings_ui(self):
        self.node_settings.user_settings.access_key = None
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = self.project.url + 'settings/'
        rv = self.app.get(url, auth=self.user.auth)
        assert_true('<label for="s3Addon">Access Key</label>' in rv.body)

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_user_settings_ui(self, mock_dropdown):
        mock_dropdown.return_value = ['mybucket']
        url = self.project.url + 'settings/'
        rv = self.app.get(url, auth=self.user.auth)
        assert_true('mybucket' in rv.body)


class TestS3ViewsCRUD(OsfTestCase):

    def setUp(self):

        super(TestS3ViewsCRUD, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3', auth=self.consolidated_auth)
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

    @mock.patch('website.addons.s3.api.S3Wrapper.get_wrapped_key')
    @mock.patch('website.addons.s3.api.S3Wrapper.from_addon')
    def test_view_file(self, mock_from_addon, mock_wrapped_key):
        mock_from_addon.return_value = create_mock_wrapper()
        mock_wrapped_key.return_value = create_mock_key()
        url = '/project/{0}/s3/view/pizza.png/'.format(self.project._id)
        res = self.app.get(
            url,
            auth=self.user.auth,
        ).maybe_follow(
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        assert_in('Delete <i class="icon-trash"></i>', res)

    @mock.patch('website.addons.s3.api.S3Wrapper.get_wrapped_key')
    @mock.patch('website.addons.s3.api.S3Wrapper.from_addon')
    def test_view_file_non_contributor(self, mock_from_addon, mock_wrapped_key):
        mock_from_addon.return_value = create_mock_wrapper()
        mock_wrapped_key.return_value = create_mock_key()
        self.project.is_public = True
        self.project.save()
        user2 = AuthUserFactory()
        url = '/project/{0}/s3/view/pizza.png/'.format(self.project._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        ).maybe_follow(
            auth=user2.auth,
        )
        assert_equal(res.status_code, 200)
        assert_not_in('Delete <i class="icon-trash"></i>', res)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_view_faux_file(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.get_wrapped_key.return_value = None
        url = '/project/{0}/s3/view/faux.sho/'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth, expect_errors=True).maybe_follow()
        assert_equals(rv.status_int, http.NOT_FOUND)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_view_upload_url(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.does_key_exist.return_value = False
        rv = self.app.post_json(self.node_url + 's3/', {'name': 'faux.sho'}, auth=self.user.auth)
        assert_true('faux.sho' in rv.body and self.node_settings.bucket in rv.body and rv.status_int == http.OK)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_download_file_faux_file(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.does_key_exist.return_value = False
        rv = self.app.post_json(self.node_url + 's3/download/', {'path': 'faux.show'}, expect_errors=True)
        assert_equals(rv.status_int, http.NOT_FOUND)

    @mock.patch('website.addons.s3.views.crud.S3Wrapper.from_addon')
    def test_get_info_for_deleting_file(self, mock_from_addon):
        mock_from_addon.return_value = mock.Mock()
        mock_from_addon.return_value.does_key_exist.return_value = False
        res = self.app.get(
            self.project.api_url_for(
                'file_delete_info',
                path='faux.sho',
            ),
            auth=self.user.auth,
        )
        assert_equals(res.status_int, http.OK)


class TestS3ViewsHgrid(OsfTestCase):

    def setUp(self):

        super(TestS3ViewsHgrid, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3', auth=self.consolidated_auth)
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()

    def test_data_contents_no_user_settings(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = "/api/v1/project/{0}/s3/hgrid/".format(self.project._id)
        rv = self.app.get(url, expect_errors=True, auth=self.user.auth)
        assert_equals(rv.status_int, http.BAD_REQUEST)

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


class TestCreateBucket(OsfTestCase):

    def setUp(self):

        super(TestCreateBucket, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3', auth=self.consolidated_auth)
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()

    def test_bad_names(self):
        assert_false(validate_bucket_name('bogus naMe'))
        assert_false(validate_bucket_name(''))
        assert_false(validate_bucket_name('no'))
        assert_false(validate_bucket_name('.cantstartwithp'))
        assert_false(validate_bucket_name('or.endwith.'))
        assert_false(validate_bucket_name('..nodoubles'))
        assert_false(validate_bucket_name('no_unders_in'))

    def test_names(self):
        assert_true(validate_bucket_name('imagoodname'))
        assert_true(validate_bucket_name('still.passing'))
        assert_true(validate_bucket_name('can-have-dashes'))
        assert_true(validate_bucket_name('kinda.name.spaced'))

    @mock.patch('website.addons.s3.views.crud.create_bucket')
    def test_create_bucket_pass(self, mock_make):
        mock_make.return_value = True
        url = "/api/v1/project/{0}/s3/newbucket/".format(self.project._id)
        rv = self.app.post_json(url, {'bucket_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)

        assert_equals(rv.status_int, http.OK)

    @mock.patch('website.addons.s3.views.crud.create_bucket')
    def test_create_bucket_fail(self, mock_make):
        error = S3ResponseError(418, 'because Im a test')
        error.message = 'This should work'
        mock_make.side_effect = error

        url = "/api/v1/project/{0}/s3/newbucket/".format(self.project._id)
        rv = self.app.post_json(url, {'bucket_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)

        assert_equals(rv.body, '{"message": "This should work"}')
#TODO
#removed access key
#
