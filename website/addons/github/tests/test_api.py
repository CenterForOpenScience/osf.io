# -*- coding: utf-8 -*-
import mock
import unittest
from nose.tools import *
from tests.factories import ProjectFactory, UserFactory
from tests.base import DbTestCase
from utils import create_mock_github
from website.addons.github import api


class TestGithubApi(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('github')
        self.project.creator.add_addon('github')

        self.github = create_mock_github(user='octocat', private=False)

        self.node_settings = self.project.get_addon('github')
        self.node_settings.user_settings = self.project.creator.get_addon('github')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.github.repo.return_value['owner']['login']
        self.node_settings.repo = self.github.repo.return_value['name']
        self.node_settings.save()

    # TODO: Check for completeness
    def test_tree_to_hgrid(self):
        tree = self.github.tree(user='octocat', repo='hello', sha='12345abc')['tree']
        res = api.tree_to_hgrid(
            tree, user='octocat', repo='hello', node=self.project,
            node_settings=self.node_settings,
        )
        assert_equal(len(res), 3)
        assert_equal(
            'github:{0}:{1}'.format(
                self.node_settings._id,
                tree[0]['path']
            ),
            res[0]['uid']
        )
        assert_in(res[0]['name'], tree[0]['path'])
        assert_equal(res[0]['parent_uid'], 'null')
        assert_equal(res[0]['type'], 'file')
        assert_equal(len(res[0]['size']), 2)
        assert_equal(res[0]['size'][0], tree[0]['size'])
        assert_equal(res[0]['ext'], '')

        # Test URLs
        assert_equal(
            res[0]['view'],
            '/{0}/github/file/{1}/'.format(
                self.project._id,
                tree[0]['path']
            )
        )
        assert_equal(
            res[0]['delete'],
            '/api/v1/project/{0}/github/file/{1}/'.format(
                self.project._id,
                tree[0]['path']
            )
        )
        # Files should not have lazy-load or upload URLs
        assert_not_in('lazyLoad', res[0])
        assert_not_in('uploadUrl', res[0])
