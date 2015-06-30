import httplib as http

import mock
from faker import Faker
from nose.tools import *  # noqa
from boto.exception import S3ResponseError

from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory

from website.addons.s3.settings import DEFAULT_BUCKET_LOCATION
from website.addons.s3.utils import validate_bucket_name, valid_bucket_location
from website.util import api_url_for


fake = Faker()


class MockS3Bucket(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class TestS3ViewsConfig(OsfTestCase):

    def setUp(self):
        super(TestS3ViewsConfig, self).setUp()
        self.patcher = mock.patch('website.addons.s3.model.AddonS3UserSettings.is_valid', new=True)
        self.patcher.start()

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

    def tearDown(self):
        super(TestS3ViewsConfig, self).tearDown()
        self.patcher.stop()

    def test_s3_settings_no_bucket(self):
        rv = self.app.post_json(
            self.project.api_url_for('s3_post_node_settings'),
            {}, expect_errors=True, auth=self.user.auth
        )
        assert_in('trouble', rv.body)

    @mock.patch('website.addons.s3.views.config.utils.bucket_exists')
    def test_s3_set_bucket(self, mock_exists):
        mock_exists.return_value = True
        url = self.project.api_url_for('s3_post_node_settings')
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
        url = self.project.api_url_for('s3_post_node_settings')
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_s3_set_bucket_no_auth(self):

        user = AuthUserFactory()
        user.add_addon('s3')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('s3_post_node_settings')
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
        url = self.project.api_url_for('s3_post_node_settings')
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_s3_set_bucket_registered(self):
        registration = self.project.register_node(
            None, self.consolidated_auth, '', ''
        )

        url = registration.api_url_for('s3_post_node_settings')
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=self.user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=True)
    def test_user_settings(self, _):
        url = self.project.api_url_for('s3_post_user_settings')
        self.app.post_json(
            url,
            {
                'access_key': 'Steven Hawking',
                'secret_key': 'Atticus Fitch killing mocking'
            },
            auth=self.user.auth
        )
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'Steven Hawking')
        assert_equals(self.user_settings.secret_key, 'Atticus Fitch killing mocking')

    def test_s3_remove_user_settings(self):
        self.user_settings.access_key = 'to-kill-a-mocking-bucket'
        self.user_settings.secret_key = 'itsasecret'
        self.user_settings.save()
        url = api_url_for('s3_delete_user_settings')
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, None)
        assert_equals(self.user_settings.secret_key, None)

    def test_s3_remove_user_settings_none(self):
        self.user_settings.access_key = None
        self.user_settings.secret_key = None
        self.user_settings.save()
        url = api_url_for('s3_delete_user_settings')
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=False)
    def test_user_settings_cant_list(self, mock_can_list):
        url = api_url_for('s3_post_user_settings')
        rv = self.app.post_json(url, {
            'access_key': 'aldkjf',
            'secret_key': 'las'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('Unable to list buckets.', rv.body)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=True)
    def test_node_settings_no_user_settings(self, mock_can_list):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = self.project.api_url_for('s3_authorize_node')

        self.app.post_json(url, {'access_key': 'scout', 'secret_key': 'ssshhhhhhhhh'}, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    @mock.patch('website.addons.s3.views.config.utils.get_bucket_names')
    def test_s3_bucket_list(self, mock_bucket_list):
        fake_buckets = []
        for _ in range(10):
            fake_bucket = mock.Mock()
            fake_bucket.name = fake.domain_word()
            fake_bucket.append(fake_bucket)

        mock_bucket_list.return_value = fake_buckets
        url = self.node_settings.owner.api_url_for('s3_get_bucket_list')
        ret = self.app.get(url, auth=self.user.auth)

        assert_equals(ret.json, {'buckets': [bucket.name for bucket in fake_buckets]})

    def test_s3_remove_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('s3_delete_node_settings')
        ret = self.app.delete(url, auth=self.user.auth)

        assert_equal(ret.json['has_bucket'], False)
        assert_equal(ret.json['node_has_auth'], False)

    def test_s3_remove_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('s3_delete_node_settings')
        ret = self.app.delete(url, auth=None, expect_errors=True)

        assert_equal(ret.status_code, 401)

    def test_s3_get_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('s3_get_node_settings')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json['result']

        assert_equal(result['node_has_auth'], True)
        assert_equal(result['user_is_owner'], True)
        assert_equal(result['bucket'], self.node_settings.bucket)

    def test_s3_get_node_settings_not_owner(self):
        url = self.node_settings.owner.api_url_for('s3_get_node_settings')
        non_owner = AuthUserFactory()
        self.project.add_contributor(non_owner, save=True, permissions=['write'])
        res = self.app.get(url, auth=non_owner.auth)

        result = res.json['result']
        assert_equal(result['bucket'], self.node_settings.bucket)
        assert_equal(result['node_has_auth'], True)
        assert_equal(result['user_is_owner'], False)

    def test_s3_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('s3_get_node_settings')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=True)
    def test_s3_authorize_node_valid(self, _):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth)
        assert_equal(res.json['node_has_auth'], True)

    def test_s3_authorize_node_malformed(self):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=False)
    def test_s3_authorize_node_invalid(self, _):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('Unable to list buckets', res.json['message'])
        assert_equal(res.status_code, 400)

    def test_s3_authorize_node_unauthorized(self):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        unauthorized = AuthUserFactory()
        res = self.app.post_json(url, cred, auth=unauthorized.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=True)
    def test_s3_authorize_user_valid(self, _):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_s3_authorize_user_malformed(self):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=False)
    def test_s3_authorize_user_invalid(self, _):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('Unable to list buckets', res.json['message'])
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.views.config.utils.can_list', return_value=True)
    def test_s3_node_import_auth_authorized(self, _):
        url = self.project.api_url_for('s3_node_import_auth')
        self.node_settings.deauthorize(auth=None, save=True)
        res = self.app.post(url, auth=self.user.auth)
        assert_equal(res.json['node_has_auth'], True)
        assert_equal(res.json['user_is_owner'], True)

    def test_s3_node_import_auth_unauthorized(self):
        url = self.project.api_url_for('s3_node_import_auth')
        self.node_settings.deauthorize(auth=None, save=True)
        unauthorized = AuthUserFactory()
        res = self.app.post(url, auth=unauthorized.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

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

    def test_bad_locations(self):
        assert_false(valid_bucket_location('Venus'))
        assert_false(valid_bucket_location('AlphaCentari'))
        assert_false(valid_bucket_location('CostaRica'))

    def test_locations(self):
        assert_true(valid_bucket_location(DEFAULT_BUCKET_LOCATION['value']))
        assert_true(valid_bucket_location('EU'))
        assert_true(valid_bucket_location('us-west-1'))

    @mock.patch('website.addons.s3.views.crud.utils.create_bucket')
    @mock.patch('website.addons.s3.views.crud.utils.get_bucket_names')
    def test_create_bucket_pass(self, mock_names, mock_make):
        mock_make.return_value = True
        mock_names.return_value = [
            'butintheend',
            'it',
            'doesntevenmatter'
        ]
        url = self.project.api_url_for('create_bucket')
        ret = self.app.post_json(
            url,
            {
                'bucket_name': 'doesntevenmatter',
                'bucket_location': DEFAULT_BUCKET_LOCATION['value'],
            },
            auth=self.user.auth
        )

        assert_equals(ret.status_int, http.OK)
        assert_in('doesntevenmatter', ret.json['buckets'])

    @mock.patch('website.addons.s3.views.crud.utils.create_bucket')
    def test_create_bucket_fail(self, mock_make):
        error = S3ResponseError(418, 'because Im a test')
        error.message = 'This should work'
        mock_make.side_effect = error

        url = "/api/v1/project/{0}/s3/newbucket/".format(self.project._id)
        ret = self.app.post_json(url, {'bucket_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)

        assert_equals(ret.body, '{"message": "This should work", "title": "Problem connecting to S3"}')

    @mock.patch('website.addons.s3.views.crud.utils.create_bucket')
    def test_bad_location_fails(self, mock_make):
        url = "/api/v1/project/{0}/s3/newbucket/".format(self.project._id)
        ret = self.app.post_json(
            url,
            {
                'bucket_name': 'doesntevenmatter',
                'bucket_location': 'not a real bucket location',
            },
            auth=self.user.auth,
            expect_errors=True)

        assert_equals(ret.body, '{"message": "That bucket location is not valid.", "title": "Invalid bucket location"}')
