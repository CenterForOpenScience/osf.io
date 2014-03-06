import mock
import unittest
from nose.tools import *
from webtest_plus import TestApp

import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory

from framework.auth.decorators import Auth
from website.addons.figshare import settings as figshare_settings

from utils import create_mock_figshare

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class TestViewsConfig(DbTestCase):

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
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

    def test_config_no_change(self):
        num = len(self.project.logs)
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_id': 'project_123456'}, auth=self.user.auth)
        self.project.reload()

        assert_equal(rv.status_int, 200)
        assert_equal(len(self.project.logs), num)

    def test_config_change(self):
        num = len(self.project.logs)
        url = '/api/v1/project/{0}/figshare/settings/'.format(self.project._id)
        rv = self.app.post_json(url, {'figshare_id': 'project_9001'}, auth=self.user.auth)
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


class TestViewsCrud(DbTestCase):

    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def setUp(self, mock_fs):

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
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

        self.figshare = create_mock_figshare('test')

    def test_publish_no_category(self):
        url = '/api/v1/project/{0}/figshare/publish/article/9002/'.format(self.project._id)
        rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        self.node_settings.reload()
        self.project.reload()

        assert_equal(rv.status_int, 400)

    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def test_view_missing(self, mock_fig):
        mock_fig.return_value = self.figshare
        url = '/project/{0}/figshare/article/564/file/134880423/'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth, expect_errors=True).maybe_follow()
        assert_equal(rv.status_int, 404)

    #TODO Fix me, not logged in?
    @mock.patch('website.addons.figshare.api.Figshare.from_settings')
    def test_view_private(self, mock_fig):
        mock_fig.return_value = self.figshare
        url = '/project/{0}/figshare/article/564/file/1348803/'.format(self.project._id)
        rv = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(rv.status_int, 200)
        rv.showbrowser()
        assert_true('file is unpublished we cannot render it.' in rv.body)
