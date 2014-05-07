from nose.tools import *
from webtest_plus import TestApp

import website.app
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory

from framework.auth.decorators import Auth
from website.addons.figshare import settings as figshare_settings

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.non_authenticator = AuthUserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )

        self.project.add_addon('figshare', auth=self.consolidated_auth)
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.user_settings.oauth_access_token = 'legittoken'
        self.user_settings.oauth_access_token_secret = 'legittoken'
        self.user_settings.save()
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.figshare_type = 'project'
        self.node_settings.figshare_title = 'singlefile'
        self.node_settings.save()

    def test_update_fields_project(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'project',
            'id': '313131',
            'title': 'A PROJECT'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_type, 'project')
        assert_equals(self.node_settings.figshare_title, 'A PROJECT')
        # check for log added
        assert_equals(len(self.project.logs), num_logs+1)

    def test_update_fields_fileset(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'fileset',
            'id': '313131',
            'title': 'A FILESET'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_type, 'fileset')
        assert_equals(self.node_settings.figshare_title, 'A FILESET')
        # check for log added
        assert_equals(len(self.project.logs), num_logs+1)

    def test_update_fields_some_missing(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'project',
            'id': '313131',
            'title': 'A PROJECT'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_title, 'A PROJECT')
        # check for log added
        assert_equals(len(self.project.logs), num_logs+1)

    def test_update_fields_invalid(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'adad' : 131313,
            'i1513': '313131',
            'titladad': 'A PROJECT'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '123456')
        assert_equals(self.node_settings.figshare_type, 'project')
        assert_equals(self.node_settings.figshare_title, 'singlefile')
        # check for log added
        assert_equals(len(self.project.logs), num_logs)

    def test_node_settings_article(self):
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_value': 'article_9001', 'figshare_title': 'newName'}, expect_errors=True, auth=self.user.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 400)
        assert_equal(self.node_settings.figshare_id, '123456')

    def test_node_settings_fileset(self):
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_value': 'fileset_9002', 'figshare_title': 'newFeatureYAY'}, expect_errors=True, auth=self.user.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 200)
        assert_equal(self.node_settings.figshare_id, '9002')

    def test_node_settings_none(self):
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_id': ''}, expect_errors=True, auth=self.user.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 400)
        assert_equal(self.node_settings.figshare_id, '123456')

    def test_node_settings_bad(self):
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_id': 'iamnothing', 'figshare_title': 'alsonothing'}, expect_errors=True, auth=self.user.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 400)
        assert_equal(self.node_settings.figshare_id, '123456')

    def test_unlink_as_other(self):
        url = '/api/v1/project/{0}/figshare/unlink/'.format(self.project._id)
        rv = self.app.post(url, expect_errors=True, auth=self.non_authenticator.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 400)
        assert_true(self.node_settings.figshare_id != None)

    def test_unlink(self):
        url = '/api/v1/project/{0}/figshare/unlink/'.format(self.project._id)
        rv = self.app.post(url, auth=self.user.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 200)
        assert_true(self.node_settings.figshare_id == None)

    def test_node_settings_project(self):
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_value': 'project_9001', 'figshare_title': 'newName'}, auth=self.user.auth)
        self.node_settings.reload()
        assert_equal(rv.status_int, 200)
        assert_equal(self.node_settings.figshare_id, '9001')

    def test_api_url_no_user(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        assert_equal(self.node_settings.api_url, figshare_settings.API_URL)

    def test_api_url(self):
        assert_equal(self.node_settings.api_url, figshare_settings.API_OAUTH_URL)

    def test_before_remove_contributor_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.project.creator
        )
        assert_true(message)

    def test_before_remove_contributor_not_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.non_authenticator
        )
        assert_false(message)

    def test_after_remove_contributor_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.project.creator
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert_equal(
            self.node_settings.user_settings,
            clone.user_settings,
        )

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert_equal(
            clone.user_settings,
            None,
        )

        #TODO Test figshare options and figshare to_json
    
