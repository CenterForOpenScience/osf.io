# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)
import httplib as http

from tests.factories import ProjectFactory, UserFactory, RegistrationFactory, NodeFactory, NodeLogFactory, AuthUserFactory
from tests.base import OsfTestCase

from framework.auth import Auth
from framework import utils as framework_utils
from website.project.views.node import _get_summary
from website.profile import utils
from website.views import serialize_log


class TestNodeSerializers(OsfTestCase):

    # Regression test for #489
    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_get_summary_private_node_should_include_id_and_primary_boolean_reg_and_fork(self):
        user = UserFactory()
        # user cannot see this node
        node = ProjectFactory(public=False)
        result = _get_summary(
            node, auth=Auth(user),
            rescale_ratio=None,
            primary=True,
            link_id=None
        )

        # serialized result should have id and primary
        assert_equal(result['summary']['id'], node._primary_key)
        assert_true(result['summary']['primary'], True)
        assert_equal(result['summary']['is_registration'], node.is_registration)
        assert_equal(result['summary']['is_fork'], node.is_fork)

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/668
    def test_get_summary_for_registration_uses_correct_date_format(self):
        reg = RegistrationFactory()
        res = _get_summary(reg, auth=Auth(reg.creator), rescale_ratio=None)
        assert_equal(res['summary']['registered_date'],
                reg.registered_date.strftime('%Y-%m-%d %H:%M UTC'))

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/858
    def test_get_summary_private_registration_should_include_is_registration(self):
        user = UserFactory()
        # non-contributor cannot see private registration of public project
        node = ProjectFactory(public=True)
        reg = RegistrationFactory(project=node, user=node.creator)
        res = _get_summary(reg, auth=Auth(user), rescale_ratio=None)

        # serialized result should have is_registration
        assert_true(res['summary']['is_registration'])

    def test_get_summary_private_fork_should_include_is_fork(self):
        user = UserFactory()
        # non-contributor cannot see private fork of public project
        node = ProjectFactory(public=True)
        consolidated_auth = Auth(user=node.creator)
        fork = node.fork_node(consolidated_auth)

        res = _get_summary(
            fork, auth=Auth(user),
            rescale_ratio=None,
            primary=True,
            link_id=None
        )
        # serialized result should have is_fork
        assert_true(res['summary']['is_fork'])

    def test_get_summary_private_fork_private_project_should_include_is_fork(self):
        # contributor on a private project
        user = UserFactory()
        node = ProjectFactory(public=False)
        node.add_contributor(user)

        # contributor cannot see private fork of this project
        consolidated_auth = Auth(user=node.creator)
        fork = node.fork_node(consolidated_auth)

        res = _get_summary(
            fork, auth=Auth(user),
            rescale_ratio=None,
            primary=True,
            link_id=None
        )
        # serialized result should have is_fork
        assert_false(res['summary']['can_view'])
        assert_true(res['summary']['is_fork'])

class TestNodeLogSerializers(OsfTestCase):

    def test_serialize_log(self):
        node = NodeFactory(category='hypothesis')
        log = NodeLogFactory(params={'node': node._primary_key})
        node.logs.append(log)
        node.save()
        d = serialize_log(log)
        assert_equal(d['action'], log.action)
        assert_equal(d['node']['node_type'], 'component')
        assert_equal(d['node']['category'], 'Hypothesis')

        assert_equal(d['node']['url'], log.node.url)
        assert_equal(d['date'], framework_utils.rfcformat(log.date))
        assert_in('contributors', d)
        assert_equal(d['user']['fullname'], log.user.fullname)
        assert_equal(d['user']['url'], log.user.url)
        assert_in('api_key', d)
        assert_equal(d['params'], log.params)
        assert_equal(d['node']['title'], log.node.title)

    def test_serialize_node_for_logs(self):
        node = NodeFactory()
        d = node.serialize()

        assert_equal(d['id'], node._primary_key)
        assert_equal(d['category'], node.category_display)
        assert_equal(d['node_type'], node.project_or_component)
        assert_equal(d['url'], node.url)
        assert_equal(d['title'], node.title)
        assert_equal(d['api_url'], node.api_url)
        assert_equal(d['is_public'], node.is_public)
        assert_equal(d['is_registration'], node.is_registration)

class TestAddContributorJson(OsfTestCase):

    def setUp(self):
        super(TestAddContributorJson, self).setUp()
        self.user = UserFactory()
        self.profile = self.user.profile_url
        self.user_id = self.user._primary_key
        self.fullname = self.user.fullname
        self.username = self.user.username

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
        user_info = utils.add_contributor_json(self.user)

        assert_equal(user_info['fullname'], self.fullname)
        assert_equal(user_info['email'], self.username)
        assert_equal(user_info['id'], self.user_id)
        assert_equal(user_info['employment'], None)
        assert_equal(user_info['education'], None)
        assert_equal(user_info['n_projects_in_common'], 0)
        assert_equal(user_info['registered'], True)
        assert_equal(user_info['active'], True)
        assert_in('secure.gravatar.com', user_info['gravatar_url'])
        assert_equal(user_info['profile_url'], self.profile)

    def test_add_contributor_json_with_edu(self):
        # Test user with only education information
        self.user.schools = self.schools
        user_info = utils.add_contributor_json(self.user)

        assert_equal(user_info['fullname'], self.fullname)
        assert_equal(user_info['email'], self.username)
        assert_equal(user_info['id'], self.user_id)
        assert_equal(user_info['employment'], None)
        assert_equal(user_info['education'], self.user.schools[0]['institution'])
        assert_equal(user_info['n_projects_in_common'], 0)
        assert_equal(user_info['registered'], True)
        assert_equal(user_info['active'], True)
        assert_in('secure.gravatar.com', user_info['gravatar_url'])
        assert_equal(user_info['profile_url'], self.profile)

    def test_add_contributor_json_with_job(self):
        # Test user with only employment information
        self.user.jobs = self.jobs
        user_info = utils.add_contributor_json(self.user)

        assert_equal(user_info['fullname'], self.fullname)
        assert_equal(user_info['email'], self.username)
        assert_equal(user_info['id'], self.user_id)
        assert_equal(user_info['employment'], self.user.jobs[0]['institution'])
        assert_equal(user_info['education'], None)
        assert_equal(user_info['n_projects_in_common'], 0)
        assert_equal(user_info['registered'], True)
        assert_equal(user_info['active'], True)
        assert_in('secure.gravatar.com', user_info['gravatar_url'])
        assert_equal(user_info['profile_url'], self.profile)

    def test_add_contributor_json_with_job_and_edu(self):
        # User with both employment and education information
        self.user.jobs = self.jobs
        self.user.schools = self.schools
        user_info = utils.add_contributor_json(self.user)

        assert_equal(user_info['fullname'], self.fullname)
        assert_equal(user_info['email'], self.username)
        assert_equal(user_info['id'], self.user_id)
        assert_equal(user_info['employment'], self.user.jobs[0]['institution'])
        assert_equal(user_info['education'], self.user.schools[0]['institution'])
        assert_equal(user_info['n_projects_in_common'], 0)
        assert_equal(user_info['registered'], True)
        assert_equal(user_info['active'], True)
        assert_in('secure.gravatar.com', user_info['gravatar_url'])
        assert_equal(user_info['profile_url'], self.profile)

