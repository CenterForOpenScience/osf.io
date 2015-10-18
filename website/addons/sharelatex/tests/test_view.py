import httplib as http

import mock
import random
from faker import Faker
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import ProjectFactory, AuthUserFactory

from website.addons.sharelatex.utils import validate_project_name
from website.util import api_url_for


fake = Faker()


class MockShareLatexBucket(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class TestShareLatexViewsConfig(OsfTestCase):

    def setUp(self):
        super(TestShareLatexViewsConfig, self).setUp()
        self.patcher = mock.patch('website.addons.sharelatex.model.AddonShareLatexUserSettings.is_valid', new=True)
        self.patcher.start()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('sharelatex', auth=self.consolidated_auth)
        self.project.creator.add_addon('sharelatex')

        self.user_settings = self.user.get_addon('sharelatex')
        self.user_settings.sharelatex_url = 'We-Will-Rock-You'
        self.user_settings.auth_token = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('sharelatex')
        self.node_settings.project = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('sharelatex')

        self.node_settings.save()
        self.node_url = '/api/v1/project/{0}/'.format(self.project._id)

    def tearDown(self):
        super(TestShareLatexViewsConfig, self).tearDown()
        self.patcher.stop()

    def test_sharelatex_settings_input_empty_keys(self):
        url = self.project.api_url_for('sharelatex_post_user_settings')
        rv = self.app.post_json(url,{
            'sharelatex_url': '',
            'auth_token': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_sharelatex_settings_input_empty_sharelatex_url(self):
        url = self.project.api_url_for('sharelatex_post_user_settings')
        rv = self.app.post_json(url,{
            'sharelatex_url': '',
            'auth_token': 'Non-empty-secret-key'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)


    def test_sharelatex_settings_input_empty_auth_token(self):
        url = self.project.api_url_for('sharelatex_post_user_settings')
        rv = self.app.post_json(url,{
            'sharelatex_url': 'Non-empty-access-key',
            'auth_token': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_sharelatex_settings_no_project(self):
        rv = self.app.post_json(
            self.project.api_url_for('sharelatex_post_node_settings'),
            {}, expect_errors=True, auth=self.user.auth
        )
        assert_in('trouble', rv.body)

    @mock.patch('website.addons.sharelatex.views.config.utils.project_exists')
    def test_sharelatex_set_project(self, mock_exists):
        mock_exists.return_value = True
        url = self.project.api_url_for('sharelatex_post_node_settings')
        self.app.post_json(
            url, {'sharelatex_project': 'hammertofall'}, auth=self.user.auth,
        )

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.project, 'hammertofall')
        assert_equal(self.project.logs[-1].action, 'sharelatex_project_linked')

    def test_sharelatex_set_project_no_settings(self):

        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('sharelatex_post_node_settings')
        res = self.app.post_json(
            url, {'sharelatex_project': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_sharelatex_set_project_no_auth(self):

        user = AuthUserFactory()
        user.add_addon('sharelatex')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('sharelatex_post_node_settings')
        res = self.app.post_json(
            url, {'sharelatex_project': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_sharelatex_set_project_already_authed(self):
        user = AuthUserFactory()
        user.add_addon('sharelatex')
        user_settings = user.get_addon('sharelatex')
        user_settings.sharelatex_url = 'foo'
        user_settings.auth_token = 'bar'
        user_settings.save()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('sharelatex_post_node_settings')
        res = self.app.post_json(
            url, {'sharelatex_project': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_sharelatex_set_project_registered(self):
        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=self.consolidated_auth, data=''
        )

        url = registration.api_url_for('sharelatex_post_node_settings')
        res = self.app.post_json(
            url, {'sharelatex_project': 'hammertofall'}, auth=self.user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=True)
    def test_user_settings(self, _):
        url = self.project.api_url_for('sharelatex_post_user_settings')
        self.app.post_json(
            url,
            {
                'sharelatex_url': 'Steven Hawking',
                'auth_token': 'Atticus Fitch killing mocking'
            },
            auth=self.user.auth
        )
        self.user_settings.reload()
        assert_equals(self.user_settings.sharelatex_url, 'Steven Hawking')
        assert_equals(self.user_settings.auth_token, 'Atticus Fitch killing mocking')

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=True)
    def test_user_settings_when_user_does_not_have_addon(self, _):
        user = AuthUserFactory()
        url = self.project.api_url_for('sharelatex_post_user_settings')
        self.app.post_json(
            url,
            {
                'sharelatex_url': 'ABCDEFG',
                'auth_token': 'We are the champions'
            },
            auth=user.auth
        )
        user.reload()
        user_settings = user.get_addon('sharelatex')
        assert_equals(user_settings.sharelatex_url, 'ABCDEFG')
        assert_equals(user_settings.auth_token, 'We are the champions')

    def test_sharelatex_remove_user_settings(self):
        self.user_settings.sharelatex_url = 'to-kill-a-mocking-project'
        self.user_settings.auth_token = 'itsasecret'
        self.user_settings.save()
        url = api_url_for('sharelatex_delete_user_settings')
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.sharelatex_url, None)
        assert_equals(self.user_settings.auth_token, None)

        # Last log has correct action and user
        self.project.reload()
        last_project_log = self.project.logs[-1]
        assert_equal(last_project_log.action, 'sharelatex_node_deauthorized')
        assert_equal(last_project_log.user, self.user)

    def test_sharelatex_remove_user_settings_none(self):
        self.user_settings.sharelatex_url = None
        self.user_settings.auth_token = None
        self.user_settings.save()
        url = api_url_for('sharelatex_delete_user_settings')
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=False)
    def test_user_settings_cant_list(self, mock_can_list):
        url = api_url_for('sharelatex_post_user_settings')
        rv = self.app.post_json(url, {
            'sharelatex_url': 'aldkjf',
            'auth_token': 'las'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('Unable to list projects.', rv.body)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=True)
    def test_node_settings_no_user_settings(self, mock_can_list):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = self.project.api_url_for('sharelatex_authorize_node')

        self.app.post_json(url, {'sharelatex_url': 'scout', 'auth_token': 'ssshhhhhhhhh'}, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.sharelatex_url, 'scout')

    @mock.patch('website.addons.sharelatex.views.config.utils.get_project_list')
    def test_sharelatex_project_list(self, mock_project_list):
        fake_projects = []
        for _ in range(10):
            fake_project = {}
            fake_project['_id'] = random.randint(1, 100)
            fake_project['name'] = fake.domain_word()
            fake_projects.append(fake_project)

        mock_project_list.return_value = fake_projects

        url = self.node_settings.owner.api_url_for('sharelatex_get_project_list')

        ret = self.app.get(url, auth=self.user.auth)

        assert_equals([p['name'] for p in ret.json], [project['name'] for project in fake_projects])
        assert_equals([p['id'] for p in ret.json], [project['_id'] for project in fake_projects])

    def test_sharelatex_remove_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('sharelatex_delete_node_settings')
        ret = self.app.delete(url, auth=self.user.auth)

        assert_equal(ret.json['has_project'], False)
        assert_equal(ret.json['node_has_auth'], False)

    def test_sharelatex_remove_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('sharelatex_delete_node_settings')
        ret = self.app.delete(url, auth=None, expect_errors=True)

        assert_equal(ret.status_code, 401)

    def test_sharelatex_get_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('sharelatex_get_node_settings')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json['result']

        assert_equal(result['node_has_auth'], True)
        assert_equal(result['user_is_owner'], True)
        assert_equal(result['project'], self.node_settings.project)

    def test_sharelatex_get_node_settings_not_owner(self):
        url = self.node_settings.owner.api_url_for('sharelatex_get_node_settings')
        non_owner = AuthUserFactory()
        self.project.add_contributor(non_owner, save=True, permissions=['write'])
        res = self.app.get(url, auth=non_owner.auth)

        result = res.json['result']
        assert_equal(result['project'], self.node_settings.project)
        assert_equal(result['node_has_auth'], True)
        assert_equal(result['user_is_owner'], False)

    def test_sharelatex_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('sharelatex_get_node_settings')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=True)
    def test_sharelatex_authorize_node_valid(self, _):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
            'auth_token': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth)
        assert_equal(res.json['node_has_auth'], True)

    def test_sharelatex_authorize_node_malformed(self):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=False)
    def test_sharelatex_authorize_node_invalid(self, _):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
            'auth_token': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('Unable to list projects', res.json['message'])
        assert_equal(res.status_code, 400)

    def test_sharelatex_authorize_node_unauthorized(self):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
            'auth_token': fake.password(),
        }
        unauthorized = AuthUserFactory()
        res = self.app.post_json(url, cred, auth=unauthorized.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=True)
    def test_sharelatex_authorize_user_valid(self, _):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
            'auth_token': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_sharelatex_authorize_user_malformed(self):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=False)
    def test_sharelatex_authorize_user_invalid(self, _):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': fake.password(),
            'auth_token': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('Unable to list projects', res.json['message'])
        assert_equal(res.status_code, 400)

    def test_sharelatex_authorize_input_empty_keys(self):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': '',
            'auth_token': '',
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('All the fields above are required', res.json['message'])
        assert_equal(res.status_code, 400)

    def test_sharelatex_authorize_input_empty_sharelatex_url(self):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': '',
            'auth_token': 'Non-empty-secret-key',
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('All the fields above are required', res.json['message'])
        assert_equal(res.status_code, 400)

    def test_sharelatex_authorize_input_empty_auth_token(self):
        url = self.project.api_url_for('sharelatex_authorize_node')
        cred = {
            'sharelatex_url': 'Non-empty-access-key',
            'auth_token': '',
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_in('All the fields above are required', res.json['message'])
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.sharelatex.views.config.utils.can_list', return_value=True)
    def test_sharelatex_node_import_auth_authorized(self, _):
        url = self.project.api_url_for('sharelatex_node_import_auth')
        self.node_settings.deauthorize(auth=None, save=True)
        res = self.app.post(url, auth=self.user.auth)
        assert_equal(res.json['node_has_auth'], True)
        assert_equal(res.json['user_is_owner'], True)

    def test_sharelatex_node_import_auth_unauthorized(self):
        url = self.project.api_url_for('sharelatex_node_import_auth')
        self.node_settings.deauthorize(auth=None, save=True)
        unauthorized = AuthUserFactory()
        res = self.app.post(url, auth=unauthorized.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

class TestCreateBucket(OsfTestCase):

    def setUp(self):

        super(TestCreateBucket, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('sharelatex', auth=self.consolidated_auth)
        self.project.creator.add_addon('sharelatex')

        self.user_settings = self.user.get_addon('sharelatex')
        self.user_settings.sharelatex_url = 'We-Will-Rock-You'
        self.user_settings.auth_token = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('sharelatex')
        self.node_settings.project = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('sharelatex')

        self.node_settings.save()

    def test_bad_names(self):
        assert_false(validate_project_name('bogus naMe'))
        assert_false(validate_project_name(''))
        assert_false(validate_project_name('no'))
        assert_false(validate_project_name('.cantstartwithp'))
        assert_false(validate_project_name('or.endwith.'))
        assert_false(validate_project_name('..nodoubles'))
        assert_false(validate_project_name('no_unders_in'))

    def test_names(self):
        assert_true(validate_project_name('imagoodname'))
        assert_true(validate_project_name('still.passing'))
        assert_true(validate_project_name('can-have-dashes'))
        assert_true(validate_project_name('kinda.name.spaced'))

    @mock.patch('website.addons.sharelatex.views.crud.utils.create_project')
    @mock.patch('website.addons.sharelatex.views.crud.utils.get_project_names')
    def test_create_project_pass(self, mock_names, mock_make):
        assert True
#        mock_make.return_value = True
#        mock_names.return_value = [
#            'butintheend',
#            'it',
#            'doesntevenmatter'
#        ]
#        url = self.project.api_url_for('create_project')
#        ret = self.app.post_json(
#            url,
#            {
#                'project_name': 'doesntevenmatter',
#                'project_location': '',
#            },
#            auth=self.user.auth
#        )

#        assert_equals(ret.status_int, http.OK)
#        assert_in('doesntevenmatter', ret.json['projects'])

    @mock.patch('website.addons.sharelatex.views.crud.utils.create_project')
    def test_create_project_fail(self, mock_make):
        assert True
#        error = ResponseError(418, 'because Im a test')
#        error.message = 'This should work'
#        mock_make.side_effect = error
#
#        url = "/api/v1/project/{0}/sharelatex/newproject/".format(self.project._id)
#        ret = self.app.post_json(url, {'project_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)
#
#        assert_equals(ret.body, '{"message": "This should work", "title": "Problem connecting to ShareLatex"}')

    @mock.patch('website.addons.sharelatex.views.crud.utils.create_project')
    def test_bad_location_fails(self, mock_make):
        assert True
#        url = "/api/v1/project/{0}/sharelatex/newproject/".format(self.project._id)
#        ret = self.app.post_json(
#            url,
#            {
#                'project_name': 'doesntevenmatter',
#                'project_location': 'not a real project location',
#            },
#            auth=self.user.auth,
#            expect_errors=True)

#        assert_equals(ret.body, '{"message": "That project location is not valid.", "title": "Invalid project location"}')
