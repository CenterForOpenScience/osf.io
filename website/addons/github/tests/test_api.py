# -*- coding: utf-8 -*-

from .utils import create_mock_github

from website.addons.github import api

def test_tree_to_hgrid():
    github_mock = create_mock_github()
    tree = github_mock.tree(user='octocat', repo='hello', sha='12345abc')
    assert 0, 'finish me'
