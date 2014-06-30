# -*- coding: utf-8 -*-
import os

from nose.tools import *

from website.addons.badges.model import BadgeAssertion
from utils import *
from tests.base import OsfTestCase, fake, URLLookup
from tests.factories import AuthUserFactory, ProjectFactory

from website.app import init_app

app = init_app(set_backends=False, routes=True)
lookup = URLLookup(app)


class TestUserSettingsModel(OsfTestCase):

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


class TestNodeSettingsModel(OsfTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.project = ProjectFactory()
        self.project.add_addon('badges', self.user.auth)
        self.node_settings = self.project.get_addon('badges')

    def test_exists(self):
        assert_true(self.node_settings)

    def test_does_nothing(self):
        pass


class TestBadge(OsfTestCase):

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

    def test_assertions(self):
        create_mock_badge(self.usersettings)
        badge = self.usersettings.badges[0]
        assert_equals(len(badge.assertions), 0)
        for n in xrange(4):
            BadgeAssertion.create(badge, None)
            assert_equals(len(badge.assertions), n + 1)


class TestAssertion(OsfTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.user.add_addon('badges', override=True)
        self.usersettings = self.user.get_addon('badges', self.user.auth)
        self.usersettings.save()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('badges')
        create_mock_badge(self.usersettings)
        self.badge = self.usersettings.badges[0]

    def test_parent(self):
        assertion = BadgeAssertion.create(self.badge, self.project)
        assert_equals(assertion.badge, self.badge)

    def test_recipient(self):
        assertion = BadgeAssertion.create(self.badge, self.project)
        test_data = {
            'idenity': self.project._id,
            'type': 'osfnode',
            'hashed': False
        }
        assert_equals(assertion.recipient, test_data)

    def test_awarder(self):
        assertion = BadgeAssertion.create(self.badge, self.project)
        assert_equals(assertion.awarder, self.usersettings)
