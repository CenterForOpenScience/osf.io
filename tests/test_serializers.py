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

    def test_add_contributor_json(self):
        user = UserFactory()
        user2 = UserFactory()

        profile = user.profile_url
        user_id = user._primary_key

        profile2 = user2.profile_url
        user_id2 = user2._primary_key

        jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'position': 'Lover Boy',
            'start': None,
            'end': None,
                }]

        schools = [{
             'degree': 'Vibing',
             'institution': 'Queens University',
             'department': '',
             'location': '',
             'start': None,
             'end': None,
                }]

        # User with no employment or education info listed
        user_info = {
            'fullname': 'Freddie Mercury0',
            'email': 'fred0@example.com',
            'id': user_id,
            'employment': None,
            'education': None,
            'projects_in_common': 0,
            'registered': True,
            'active': True,
            'gravatar_url': 'https://secure.gravatar.com/avatar/fff8c77ae8f4caa3edc5ea7e7cb5533c?d=identicon&size=40',
            'profile_url': profile
        }

        assert_equal(utils.add_contributor_json(user), user_info)

        # User with only education information
        user.schools = schools
        user_with_school_info = {
            'fullname': 'Freddie Mercury0',
            'email': 'fred0@example.com',
            'id': user_id,
            'employment': None,
            'education': 'Queens University',
            'projects_in_common': 0,
            'registered': True,
            'active': True,
            'gravatar_url': 'https://secure.gravatar.com/avatar/fff8c77ae8f4caa3edc5ea7e7cb5533c?d=identicon&size=40',
            'profile_url': profile
        }

        assert_equal(utils.add_contributor_json(user), user_with_school_info)


        # User with only employment information
        user2.jobs = jobs
        user_with_job_info = {
            'fullname': 'Freddie Mercury1',
            'email': 'fred1@example.com',
            'id': user_id2,
            'employment': 'School of Lover Boys',
            'education': None,
            'projects_in_common': 0,
            'registered': True,
            'active': True,
            'gravatar_url': 'https://secure.gravatar.com/avatar/25c3085f6199613c7493a5c5183e7890?d=identicon&size=40',
            'profile_url': profile2
        }

        assert_equal(utils.add_contributor_json(user2), user_with_job_info)


        # User with both employment and education information
        user.jobs = jobs
        user.schools = schools
        user_with_both = {
            'fullname': 'Freddie Mercury0',
            'email': 'fred0@example.com',
            'id': user_id,
            'employment': 'School of Lover Boys',
            'education': 'Queens University',
            'projects_in_common': 0,
            'registered': True,
            'active': True,
            'gravatar_url': 'https://secure.gravatar.com/avatar/fff8c77ae8f4caa3edc5ea7e7cb5533c?d=identicon&size=40',
            'profile_url': profile
        }

        assert_equal(utils.add_contributor_json(user), user_with_both)
