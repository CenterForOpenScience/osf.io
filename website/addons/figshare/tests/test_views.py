import mock
import unittest
from nose.tools import *
from webtest_plus import TestApp

import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory, UserFactory

from website.addons.base import AddonError
from framework.auth.decorators import Auth
from website.addons.figshare import settings as figshare_settings
from website.addons.figshare.tests.utils import create_mock_figshare
from website.addons.figshare import views
from website.addons.figshare import utils

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

figshare_mock = create_mock_figshare(project=436)

class TestViewsHgrid(DbTestCase):

    def setUp(self):
        super(TestViewsHgrid, self).setUp()

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
        self.node_settings.figshare_type = 'singlefile'
        self.node_settings.save()
        

class TestUtils(DbTestCase):
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
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '436'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()
        
    
    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid(self, *args, **kwargs):
        project = figshare_mock.project.return_value
        hgrid = utils.project_to_hgrid(self.project, project, True)        

        assert_equals(len(hgrid), len(project['articles']))
        folders_in_project = len([a for a in project['articles'] if a['defined_type']=='fileset'])
        folders_in_hgrid = len([h for h in hgrid if type(h) is list])

        assert_equals(folders_in_project, folders_in_hgrid)
        files_in_project = 0
        files_in_hgrid = 0
        for a in project['articles']:
            if a['defined_type']=='fileset':
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
                
        assert_equals(files_in_hgrid,files_in_project)
        
class TestViewsAuth(DbTestCase):
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
    
    def test_oauth_start(self):
        
