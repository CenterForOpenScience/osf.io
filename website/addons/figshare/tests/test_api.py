import mock
import unittest
from nose.tools import *
from tests.factories import ProjectFactory, UserFactory
from tests.base import DbTestCase
from utils import create_mock_figshare
from website.addons.figshare import api
from website.addons.figshare import settings as figshare_settings

class TestFigshareApi(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('figshare', auth=self.consolidated_auth)
        self.project.creator.add_addon('figshare')

        self.figshare = create_mock_figshare(self.project._id)

        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.api_url = figshare_settings.API_URL
        self.node_settings.save()

    @mock.patch('website.addons.figshare.api.Figshare.projects')
    def test_projects(self):
        projects = self.figshare.projects(self.node_settings)

        assert_equal(len(projects), 1)
        assert_equal(projects[0]['title'], u'OSF Test')

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project(self):
        project = self.figshare.project(self.node_settings, 436)

        assert_equal(project['id'], 436)
        assert_equal(project['title'], u'OSF Test')



    # TODO: Check for completeness
    def test_tree_to_hgrid(self):
        article = self.figshare.article(self.node_settings, 902210)
        article = article['items'][0]
        res = self.figshare.article_to_hgrid(self.project, self.node_settings, article)

        assert_equal(len(res), 7)
        assert_equal(
            res[0]['id'],
            902210
        )
        assert_in(res[0]['name'], article['title'])
        assert_equal(res[0]['parent_uid'], 'null')
        assert_equal(res[0]['type'], 'folder')
        assert_equal(res[0]['size'], '6')

        # Test URLs
        # TODO implement
        '''
        assert_equal(
            res[0]['view'],
            '/{0}/github/file/{1}/'.format(
                self.project._id,
                tree[0]['path']
            )
        )
        '''
        assert_equal(
            res[0]['delete'],
            ''
        )
        assert_equal(
            res[1]['delete'],
            self.project.api_url + 'figshare/article/{0}/file/{1}/delete/'.format(article['article_id'],article['files'][0]['id'])
        )

        # Files should not have lazy-load or upload URLs
        assert_equal(res[1]['uploadUrl'], '')

