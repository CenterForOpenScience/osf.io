#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import logging

from modularodm import Q
from nose.tools import *
from tests.base import OsfTestCase

from website import models
from website.app import init_app
from scripts import utils as scripts_utils
from tests.factories import AuthUserFactory


logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    logger.info("migrating personal to profileWebsites")
            
    for user in get_users_with_social_field():
        logger.info(repr(user))
        logger.info(repr(user.social))
        if not user.social.get('profileWebsites', None):
            user.social['profileWebsites'] = []
            if user.social.get('personal'):
                migrate_personal_to_profile_websites(user)
        logger.info(repr(user.social))
        user.save()


def get_users_with_social_field():
    return models.User.find(
        Q('social', 'ne', {})
    )


def migrate_personal_to_profile_websites(user):
    user.social['profileWebsites'].append(user.social.get('personal'))


class TestMigrateProfileWebsites(OsfTestCase):

    def setUp(self):
        super(TestMigrateProfileWebsites, self).setUp()
        self.user_one = AuthUserFactory.build(
            fullname='Martin Luther King',
            social=dict(
                github='userOneGithub',
                scholar='userOneScholar',
                personal='http://www.useronewebsite.com',
                twitter='userOneTwitter',
                linkedIn='userOneLinkedIn',
                impactStory='userOneImpactStory',
                orcid='userOneOrcid',
                researcherId='userOneResearcherId',
            ),
        )
        self.user_one.save()

        self.user_two = AuthUserFactory.build(
            fullname='el-Hajj Malik el-Shabazz',
            social=dict(
                github='userTwoGithub',
                scholar='userTwoScholar',
                profileWebsites=['http://www.usertwowebsite.com'],
                twitter='userTwoTwitter',
                linkedIn='userTwoLinkedIn',
                impactStory='userTwoImpactStory',
                orcid='userTwoOrcid',
                researcherId='userTwoResearcherId'
            )
        )
        self.user_two.save()
        self.user_three = AuthUserFactory()

    def test_get_users_with_personal_website(self):
        users = []
        for user in get_users_with_personal_websites():
            users.append(user._id)
        assert_in(self.user_one._id, users)
        assert_in(self.user_two._id, users)
        assert_equal(len(users), 2)

    def test_migrate_profile_websites(self):
        main()
        self.user_one.reload()
        assert_equal(self.user_one.social['scholar'], 'userOneScholar')
        assert_equal(self.user_one.social['profileWebsites'], ['http://www.useronewebsite.com'])
        assert_equal(self.user_one.social['twitter'], 'userOneTwitter')
        assert_equal(self.user_one.social['linkedIn'], 'userOneLinkedIn')
        assert_equal(self.user_one.social['impactStory'], 'userOneImpactStory')
        assert_equal(self.user_one.social['orcid'], 'userOneOrcid')
        assert_equal(self.user_one.social['researcherId'], 'userOneResearcherId')
        self.user_two.reload()
        assert_equal(self.user_two.social['scholar'], 'userTwoScholar')
        assert_equal(self.user_two.social['profileWebsites'], ['http://www.usertwowebsite.com'])
        assert_equal(self.user_two.social['twitter'], 'userTwoTwitter')
        assert_equal(self.user_two.social['linkedIn'], 'userTwoLinkedIn')
        assert_equal(self.user_two.social['impactStory'], 'userTwoImpactStory')
        assert_equal(self.user_two.social['orcid'], 'userTwoOrcid')
        assert_equal(self.user_two.social['researcherId'], 'userTwoResearcherId')

        assert_equal(self.user_three.social, {})


if __name__ == '__main__':
    main()
