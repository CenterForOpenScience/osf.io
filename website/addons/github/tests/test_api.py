# -*- coding: utf-8 -*-
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
