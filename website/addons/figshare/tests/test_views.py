import mock
import unittest
from nose.tools import *
from webtest_plus import TestApp

import website.app
from tests.base import OsfTestCase

from tests.factories import ProjectFactory, AuthUserFactory

from website.addons.figshare.tests.utils import create_mock_figshare
from website.addons.figshare import views
from website.addons.figshare import utils

from framework.auth.decorators import Auth
from website.addons.figshare import settings as figshare_settings


app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

figshare_mock = create_mock_figshare(project=436)


class TestViewsConfig(OsfTestCase):

    def setUp(self):

        super(TestViewsConfig, self).setUp()

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
        self.node_settings.figshare_title = 'FIGSHARE_TITLE'
        self.node_settings.save()

        self.figshare = create_mock_figshare('test')

    def test_config_no_change(self):
        num = len(self.project.logs)
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(
            url, {'figshare_value': 'project_123456', 'figshare_title': 'FIGSHARE_TITLE'}, auth=self.user.auth)
        self.project.reload()

        assert_equal(rv.status_int, 200)
        assert_equal(len(self.project.logs), num)

    def test_config_change(self):
        num = len(self.project.logs)
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(
            url, {'figshare_value': 'project_9001', 'figshare_title': 'IchangedbecauseIcan'}, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        assert_equal(rv.status_int, 200)
        assert_equal(self.node_settings.figshare_id, '9001')
        assert_equal(len(self.project.logs), num + 1)
        assert_equal(self.project.logs[num].action, 'figshare_content_linked')

    def test_config_unlink(self):
        url = '/api/v1/project/{0}/figshare/unlink/'.format(self.project._id)
        rv = self.app.post(url, auth=self.user.auth)
        self.node_settings.reload()
        self.project.reload()

        assert_equal(self.project.logs[-1].action, 'figshare_content_unlinked')
        assert_equal(rv.status_int, 200)
        assert_true(self.node_settings.figshare_id == None)

    def test_config_unlink_no_node(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        self.node_settings.reload()
        url = '/api/v1/project/{0}/figshare/unlink/'.format(self.project._id)
        rv = self.app.post(url, expect_errors=True, auth=self.user.auth)
        self.project.reload()

        assert_equal(self.node_settings.figshare_id, '123456')
        assert_not_equal(self.project.logs[-1].action, 'figshare_content_unlinked')
        assert_equal(rv.status_int, 400)


class TestUtils(OsfTestCase):

    def setUp(self):
        super(TestUtils, self).setUp()

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
        self.node_settings.figshare_id = '436'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid(self, *args, **kwargs):
        project = figshare_mock.project.return_value
        hgrid = utils.project_to_hgrid(self.project, project, True)

        assert_equals(len(hgrid), len(project['articles']))
        folders_in_project = len(
            [a for a in project.get('articles') or [] if a['defined_type'] == 'fileset'])
        folders_in_hgrid = len([h for h in hgrid if type(h) is list])

        assert_equals(folders_in_project, folders_in_hgrid)
        files_in_project = 0
        files_in_hgrid = 0
        for a in project.get('articles') or []:
            if a['defined_type'] == 'fileset':
                files_in_project = files_in_project + len(a['files'])
            else:
                files_in_project = files_in_project + 1

        for a in hgrid:
            if type(a) is list:
                assert_equals(a[0]['kind'], 'file')
                files_in_hgrid = files_in_hgrid + len(a)
            else:
                assert_equals(a['kind'], 'file')
                files_in_hgrid = files_in_hgrid + 1

        assert_equals(files_in_hgrid, files_in_project)

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid_no_auth(self, project):
        project.return_value = 'notNone'
        self.node_settings.user_settings = None
        ref = views.hgrid.figshare_hgrid_data(self.node_settings, self.auth)
        assert_equal(ref, None)

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid_no_id(self, project):
        project.return_value = 'not none'
        self.node_settings.figshare_id = None
        ref = views.hgrid.figshare_hgrid_data(self.node_settings, self.auth)
        assert_equal(ref, None)

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_hgrid_deleted_project(self, project):
        project.return_value = None
        ref = views.hgrid.figshare_hgrid_data(self.node_settings, self.auth)
        assert_equal(ref, None)


class TestViewsCrud(OsfTestCase):

    def setUp(self):
        super(TestViewsCrud, self).setUp()

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
        self.node_settings.figshare_id = '436'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

        self.figshare = create_mock_figshare('test')

    # def test_publish_no_category(self):
    #     url = '/api/v1/project/{0}/figshare/publish/article/9002/'.format(self.project._id)
    #     rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
    #     self.node_settings.reload()
    #     self.project.reload()

    #     assert_equal(rv.status_int, 400)

    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def test_view_missing(self, mock_fig):
        mock_fig.return_value = self.figshare
        url = '/project/{0}/figshare/article/564/file/854280423/'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth, expect_errors=True).maybe_follow()
        assert_equal(rv.status_int, 404)

    @mock.patch('website.addons.figshare.api.Figshare.create_project')
    def test_create_project_fail(self, faux_ject):
        faux_ject.return_value = False
        url = '/api/v1/project/{0}/figshare/new/project/'.format(self.project._id)
        rv = self.app.post_json(url, {'project': 'testme'}, auth=self.user.auth, expect_errors=True)
        assert_equal(rv.status_int, 400)

    @mock.patch('website.addons.figshare.api.Figshare.create_project')
    def test_create_project_no_name(self, faux_ject):
        faux_ject.return_value = False
        url = '/api/v1/project/{0}/figshare/new/project/'.format(self.project._id)
        rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equal(rv.status_int, 400)

    @mock.patch('website.addons.figshare.api.Figshare.create_article')
    def test_create_fileset_no_name(self, faux_ject):
        faux_ject.return_value = False
        url = '/api/v1/project/{0}/figshare/new/fileset/'.format(self.project._id)
        rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equal(rv.status_int, 400)

    @mock.patch('website.addons.figshare.api.Figshare.create_article')
    def test_create_fileset_no_name(self, faux_ject):
        faux_ject.return_value = False
        url = '/api/v1/project/{0}/figshare/new/fileset/'.format(self.project._id)
        rv = self.app.post_json(url, {'name': ''}, auth=self.user.auth, expect_errors=True)
        assert_equal(rv.status_int, 400)

    @mock.patch('website.addons.figshare.api.Figshare.create_project')
    def test_create_project_empty_name(self, faux_ject):
        faux_ject.return_value = False
        url = '/api/v1/project/{0}/figshare/new/project/'.format(self.project._id)
        rv = self.app.post_json(url, {'project': ''}, auth=self.user.auth, expect_errors=True)
        assert_equal(rv.status_int, 400)

    # TODO Fix me, not logged in?
    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def test_view_private(self, mock_fig):
        mock_fig.return_value = self.figshare
        url = '/project/{0}/figshare/article/564/file/1348803/'.format(self.project._id)
        self.app.auth = self.user.auth
        resp = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(resp.status_int, 200)
        assert_true('file is unpublished we cannot render it.' in resp.body)

    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def test_view_bad_file(self, mock_fig):
        mock_fig.return_value = self.figshare
        url = '/project/{0}/figshare/article/564/file/958351351/'.format(self.project._id)
        self.app.auth = self.user.auth
        resp = self.app.get(url, expect_errors=True).maybe_follow()
        assert_equal(resp.status_int, 404)

    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def test_view_bad_article(self, mock_fig):
        mock_fig.return_value = self.figshare
        url = '/project/{0}/figshare/article/543813514/file/9/'.format(self.project._id)
        self.app.auth = self.user.auth
        resp = self.app.get(url, expect_errors=True).maybe_follow()
        assert_equal(resp.status_int, 404)

class TestViewsAuth(OsfTestCase):

    def setUp(self):
        super(TestViewsAuth, self).setUp()

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
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '436'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

    #TODO Finish me, would require a lot of mocking it seems.
    def test_oauth_fail(self):
        url = '/api/v1/project/{0}/figshare/oauth'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth).maybe_follow()
        pass


    #TODO Finish me
    def test_oauth_bad_token(self):
        pass
