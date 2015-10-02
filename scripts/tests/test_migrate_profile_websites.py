from tests.factories import UserFactory
from nose.tools import *
from tests.base import OsfTestCase
from scripts.migration.migrate_personal_to_profile_websites import main, get_users_with_social_field


class TestMigrateProfileWebsites(OsfTestCase):

    def setUp(self):
        super(TestMigrateProfileWebsites, self).setUp()
        self.user_one = UserFactory.build(
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

        self.user_two = UserFactory.build(
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

        self.user_three = UserFactory()

    def tearDown(self):
        super(TestMigrateProfileWebsites, self).tearDown()
        self.user_one.remove()
        self.user_two.remove()

    def test_get_users_with_social_field(self):
        users = []
        for user in get_users_with_social_field():
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
