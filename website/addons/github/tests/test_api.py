# -*- coding: utf-8 -*-
import mock
import unittest
from nose.tools import *
from tests.factories import ProjectFactory, UserFactory
from tests.base import DbTestCase
from .utils import create_mock_github
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

    def test_tree_to_hgrid(self):
        tree = self.github.tree(user='octocat', repo='hello', sha='12345abc')['tree']
        res = api.tree_to_hgrid(tree, user='octocat', repo='hello', node=self.project)
        assert_equal(len(res), 3)
        assert_equal(
            "{0}:__repo__||{1}".format(
                tree[0]['type'],
                tree[0]['path']
            ),
            res[0]['uid']
        )
        assert_in(res[0]['name'], tree[0]['path'])
        assert_equal(res[0]['parent_uid'], 'null')
        assert_equal(res[0]['type'], 'file')
        assert_equal(res[0]['ghPath'], tree[0]['path'])
        assert_equal(res[0]['sha'], tree[0]['sha'])
        assert_equal(res[0]['url'], tree[0]['url'])
        assert_equal(len(res[0]['size']), 2)
        assert_equal(res[0]['size'][0], tree[0]['size'])
        assert_equal(res[0]['ext'], '')
        assert_equal(
            res[0]['delete'],
            '/api/v1/project/{0}/github/file/{1}/?'.format(
                self.project._id,
                tree[0]['path']
            )
        )
        assert_equal(
            res[0]['view'],
            '/{0}/github/file/{1}/?'.format(
                self.project._id,
                tree[0]['path']
            )
        )
        assert_equal(res[0]['download'], res[0]['delete'])

