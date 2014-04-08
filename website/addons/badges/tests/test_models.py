# -*- coding: utf-8 -*-
import os

from nose.tools import *

from framework.auth.decorators import Auth
from website.addons.badges.model import (
    BadgesUserSettings, BadgesNodeSettings, Badge, BadgeAssertion
)
from utils import *
from tests.base import DbTestCase, fake, URLLookup
from tests.factories import AuthUserFactory, ProjectFactory

from website.app import init_app

app = init_app(set_backends=False, routes=True)
lookup = URLLookup(app)


class TestUserSettingsModel(DbTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.user.add_addon('badges', override=True)
        self.usersettings = self.user.get_addon('badges')
        self.usersettings.save()

    def test_can_award(self):
        assert_false(self.usersettings.can_award)
        create_mock_badge(self.usersettings)
        assert_true(self.usersettings.can_award)

    def test_to_openbadge(self):
        self.user.fullname = 'HoneyBadger'
        self.user.username = 'Honey@Badger.dundundun'
        self.user.save()

        test = {
            'name': 'HoneyBadger',
            'email': 'honey@badger.dundundun'
        }

        assert_equal(self.usersettings.to_openbadge(), test)

    def test_badges(self):
        create_mock_badge(self.usersettings)
        create_mock_badge(self.usersettings)
        assert_equal(len(self.usersettings.badges), 2)
        create_mock_badge(self.usersettings)
        assert_equal(len(self.usersettings.badges), 3)


class TestNodeSettingsModel(DbTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.project = ProjectFactory()
        self.project.add_addon('badges', self.user.auth)
        self.node_settings = self.project.get_addon('badges')

    def test_exists(self):
        assert_true(self.node_settings)

    def test_does_nothing(self):
        pass


class TestBadge(DbTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.user.add_addon('badges', override=True)
        self.usersettings = self.user.get_addon('badges', self.user.auth)
        self.usersettings.save()

    def test_fields(self):
        badgedata = create_badge_dict()
        create_mock_badge(self.usersettings, badge_data=badgedata)
        badge = self.usersettings.badges[0]
        assert_equals(badge.name, badgedata['badgeName'])
        assert_equals(badge.description, badgedata['description'])
        assert_equals(badge.image, 'temp.png')
        assert_equals(badge.criteria, badgedata['criteria'])

    def test_system_badge(self):
        create_mock_badge(self.usersettings)
        badge = self.usersettings.badges[0]
        badge.make_system_badge()
        assert_true(badge.is_system_badge)
        assert_equals(badge, Badge.get_system_badges()[0])
