# -*- coding: utf-8 -*-

from nose.tools import *  # PEP8 asserts

from tests.factories import ProjectFactory, UserFactory, RegistrationFactory
from tests.base import OsfTestCase

from framework.auth import Auth
from website.project.views.node import _get_summary
from website.profile import utils
from website.filters import gravatar
from website import settings


class TestNodeSerializers(OsfTestCase):

    # Regression test for #489
    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_get_summary_private_node_should_include_id_and_primary_boolean(self):
        user = UserFactory()
        # user cannot see this node
        node = ProjectFactory(public=False)
        result = _get_summary(node, auth=Auth(user),
            rescale_ratio=None,
            primary=True,
            link_id=None
        )

        # serialized result should have id and primary
        assert_equal(result['summary']['id'], node._primary_key)
        assert_true(result['summary']['primary'], True)

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/668
    def test_get_summary_for_registration_uses_correct_date_format(self):
        reg = RegistrationFactory()
        res = _get_summary(reg, auth=Auth(reg.creator), rescale_ratio=None)
        assert_equal(res['summary']['registered_date'],
                reg.registered_date.strftime('%Y-%m-%d %H:%M UTC'))


class TestAddContributorJson(OsfTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.profile = self.user.profile_url
        self.user_id = self.user._primary_key

        self.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'position': 'Lover Boy',
            'start': None,
            'end': None,
                }]

        self.schools = [{
            'degree': 'Vibing',
            'institution': 'Queens University',
            'department': '',
            'location': '',
            'start': None,
            'end': None,
                }]

    def test_add_contributor_json(self):
        # User with no employment or education info listed

        assert_equal(utils.add_contributor_json(self.user)['fullname'], 'Freddie Mercury0')
        assert_equal(utils.add_contributor_json(self.user)['email'], 'fred0@example.com')
        assert_equal(utils.add_contributor_json(self.user)['id'], self.user_id)
        assert_equal(utils.add_contributor_json(self.user)['employment'], None)
        assert_equal(utils.add_contributor_json(self.user)['education'], None)
        assert_equal(utils.add_contributor_json(self.user)['projects_in_common'], 0)
        assert_equal(utils.add_contributor_json(self.user)['registered'], True)
        assert_equal(utils.add_contributor_json(self.user)['active'], True)
        assert_in('secure.gravatar.com', utils.add_contributor_json(self.user)['gravatar_url'])
        assert_equal(utils.add_contributor_json(self.user)['profile_url'], self.profile)

    def test_add_contributor_json_with_edu(self):
        # Test user with only education information
        self.user.schools = self.schools

        assert_equal(utils.add_contributor_json(self.user)['fullname'], 'Freddie Mercury1')
        assert_equal(utils.add_contributor_json(self.user)['email'], 'fred1@example.com')
        assert_equal(utils.add_contributor_json(self.user)['id'], self.user_id)
        assert_equal(utils.add_contributor_json(self.user)['employment'], None)
        assert_equal(utils.add_contributor_json(self.user)['education'], 'Queens University')
        assert_equal(utils.add_contributor_json(self.user)['projects_in_common'], 0)
        assert_equal(utils.add_contributor_json(self.user)['registered'], True)
        assert_equal(utils.add_contributor_json(self.user)['active'], True)
        assert_in('secure.gravatar.com', utils.add_contributor_json(self.user)['gravatar_url'])
        assert_equal(utils.add_contributor_json(self.user)['profile_url'], self.profile)


    def test_add_contributor_json_with_job(self):
        # Test user with only employment information
        self.user.jobs = self.jobs

        assert_equal(utils.add_contributor_json(self.user)['fullname'], 'Freddie Mercury2')
        assert_equal(utils.add_contributor_json(self.user)['email'], 'fred2@example.com')
        assert_equal(utils.add_contributor_json(self.user)['id'], self.user_id)
        assert_equal(utils.add_contributor_json(self.user)['employment'], 'School of Lover Boys')
        assert_equal(utils.add_contributor_json(self.user)['education'], None)
        assert_equal(utils.add_contributor_json(self.user)['projects_in_common'], 0)
        assert_equal(utils.add_contributor_json(self.user)['registered'], True)
        assert_equal(utils.add_contributor_json(self.user)['active'], True)
        assert_in('secure.gravatar.com', utils.add_contributor_json(self.user)['gravatar_url'])
        assert_equal(utils.add_contributor_json(self.user)['profile_url'], self.profile)

    def test_add_contributor_json_with_job_and_edu(self):
        # User with both employment and education information
        self.user.jobs = self.jobs
        self.user.schools = self.schools

        assert_equal(utils.add_contributor_json(self.user)['fullname'], 'Freddie Mercury3')
        assert_equal(utils.add_contributor_json(self.user)['email'], 'fred3@example.com')
        assert_equal(utils.add_contributor_json(self.user)['id'], self.user_id)
        assert_equal(utils.add_contributor_json(self.user)['employment'], 'School of Lover Boys')
        assert_equal(utils.add_contributor_json(self.user)['education'], 'Queens University')
        assert_equal(utils.add_contributor_json(self.user)['projects_in_common'], 0)
        assert_equal(utils.add_contributor_json(self.user)['registered'], True)
        assert_equal(utils.add_contributor_json(self.user)['active'], True)
        assert_in('secure.gravatar.com', utils.add_contributor_json(self.user)['gravatar_url'])
        assert_equal(utils.add_contributor_json(self.user)['profile_url'], self.profile)

