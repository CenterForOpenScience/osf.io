import mock
import unittest
from nose.tools import *

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory

from framework.auth.decorators import Auth


class TestBadges(DbTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.save()

        self.project.add_addon('badges', auth=self.consolidated_auth)
        self.project.creator.add_addon('badges')
        self.node_settings = self.project.get_addon('badges')
        self.user_settings = self.project.creator.get_addon('badges')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()
