# -*- coding: utf-8 -*-
import mock
import unittest
from nose.tools import *
from tests.factories import ProjectFactory, UserFactory
from tests.base import OsfTestCase
from utils import create_mock_s3
from website.addons.s3 import api

# TODO: finish me
class TestS3Api(OsfTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')

        self.s3 = create_mock_s3()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.user_settings = self.project.creator.get_addon('s3')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.has_bucket = True
        self.node_settings.save()
