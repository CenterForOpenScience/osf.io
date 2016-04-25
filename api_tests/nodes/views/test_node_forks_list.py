from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from website.models import Node
from website.util import permissions

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    ForkFactory
)


class TestNodeForksList(ApiTestCase):
    def setUp(self):
        super(TestNodeForksList, self).setUp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory()
        self.private_project.add_contributor(self.user, permissions=[permissions.READ, permissions.WRITE])
        self.private_project.save()
        self.component = NodeFactory(parent=self.private_project, creator=self.user)
        self.pointer = ProjectFactory(creator=self.user)
        self.private_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_fork = ForkFactory(project=self.private_project, user=self.user)
        self.private_project_url = '/{}nodes/{}/forks/'.format(API_BASE, self.private_project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.save()
        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_project_url = '/{}nodes/{}/forks/'.format(API_BASE, self.public_project._id)
        self.public_fork = ForkFactory(project=self.public_project, user=self.user)
        self.user_two = AuthUserFactory()

    def test_can_access_public_node_forks_list_when_unauthenticated(self):
        res = self.app.get(self.public_project_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 0)
        # Fork defaults to private
        assert_equal(self.public_fork.is_public, False)

        self.public_fork.is_public = True
        self.public_fork.save()

        res = self.app.get(self.public_project_url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(self.public_fork.is_public, True)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_project.title)
        assert_equal(data['id'], self.public_fork._id)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_can_access_public_node_forks_list_authenticated_contributor(self):
        res = self.app.get(self.public_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_fork.is_public, False)
        assert_equal(len(res.json['data']), 1)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_project.title)
        assert_equal(data['id'], self.public_fork._id)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_can_access_public_node_forks_list_authenticated_non_contributor(self):
        res = self.app.get(self.public_project_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 0)
        # Fork defaults to private
        assert_equal(self.public_fork.is_public, False)

        self.public_fork.is_public = True
        self.public_fork.save()

        res = self.app.get(self.public_project_url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(self.public_fork.is_public, True)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_project.title)
        assert_equal(data['id'], self.public_fork._id)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_cannot_access_private_node_forks_list_unauthenticated(self):
        res = self.app.get(self.private_project_url, expect_errors=True)

        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_authenticated_contributor_can_access_private_node_forks_list(self):
        res = self.app.get(self.private_project_url + '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from', auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.private_project.title)
        assert_equal(data['id'], self.private_fork._id)

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert_equal(fork_contributors['attributes']['family_name'], self.user.family_name)
        assert_equal(fork_contributors['id'], self.user._id)

        forked_children = data['embeds']['children']['data'][0]
        assert_equal(forked_children['id'], self.component.forks[0]._id)
        assert_equal(forked_children['attributes']['title'], self.component.title)

        forked_node_links = data['embeds']['node_links']['data'][0]['embeds']['target_node']['data']
        assert_equal(forked_node_links['id'], self.pointer._id)
        assert_equal(forked_node_links['attributes']['title'], self.pointer.title)

        expected_logs = [log.action for log in self.private_project.logs]
        expected_logs.append(self.component.logs[0].action)
        expected_logs.append('node_forked')
        expected_logs.append('node_forked')

        forked_logs = data['embeds']['logs']['data']
        assert_equal(set(expected_logs), set(log['attributes']['action'] for log in forked_logs))
        assert_equal(len(forked_logs), 6)

        forked_from = data['embeds']['forked_from']['data']
        assert_equal(forked_from['id'], self.private_project._id)

    def test_authenticated_non_contributor_cannot_access_private_node_forks_list(self):
        res = self.app.get(self.private_project_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')


class TestNodeForkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeForkCreate, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)

        self.fork_data = {
            'data': {
                'type': 'nodes'
            }
        }

        self.fork_data_with_title = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {'title': 'My Forked Project'}
            }
        }

        self.private_project_url = '/{}nodes/{}/forks/'.format(API_BASE, self.private_project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project_url = '/{}nodes/{}/forks/'.format(API_BASE, self.public_project._id)

    def tearDown(self):
        super(TestNodeForkCreate, self).tearDown()
        Node.remove()

    def test_create_fork_from_public_project_with_new_title(self):
        res = self.app.post_json_api(self.public_project_url, self.fork_data_with_title, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.public_project.forks[0]._id)
        assert_equal(res.json['data']['attributes']['title'], self.fork_data_with_title['data']['attributes']['title'])

    def test_create_fork_from_private_project_with_new_title(self):
        res = self.app.post_json_api(self.private_project_url, self.fork_data_with_title, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.private_project.forks[0]._id)
        assert_equal(res.json['data']['attributes']['title'], self.fork_data_with_title['data']['attributes']['title'])

    def test_can_fork_public_node_logged_in(self):
        res = self.app.post_json_api(self.public_project_url, self.fork_data, auth=self.user_two.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.public_project.forks[0]._id)
        assert_equal(res.json['data']['attributes']['title'], 'Fork of ' + self.public_project.title)

    def test_cannot_fork_public_node_logged_out(self):
        res = self.app.post_json_api(self.public_project_url, self.fork_data, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_can_fork_public_node_logged_in_contributor(self):
        res = self.app.post_json_api(self.public_project_url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.public_project.forks[0]._id)
        assert_equal(res.json['data']['attributes']['title'], 'Fork of ' + self.public_project.title)

    def test_cannot_fork_private_node_logged_out(self):
        res = self.app.post_json_api(self.private_project_url, self.fork_data, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_cannot_fork_private_node_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.private_project_url, self.fork_data, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_can_fork_private_node_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_project_url + '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from', self.fork_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)

        data = res.json['data']
        assert_equal(data['attributes']['title'], 'Fork of ' + self.private_project.title)

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert_equal(fork_contributors['attributes']['family_name'], self.user.family_name)
        assert_equal(fork_contributors['id'], self.user._id)

        forked_from = data['embeds']['forked_from']['data']
        assert_equal(forked_from['id'], self.private_project._id)

    def test_fork_private_components_no_access(self):
        url = self.public_project_url + '?embed=children'
        private_component = NodeFactory(parent=self.public_project, creator=self.user_two, is_public=False)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user_three.auth)
        assert_equal(res.status_code, 201)
        # Private components that you do not have access to are not forked
        assert_equal(res.json['data']['embeds']['children']['links']['meta']['total'], 0)

    def test_fork_components_you_can_access(self):
        url = self.private_project_url + '?embed=children'
        new_component = NodeFactory(parent=self.private_project, creator=self.user)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['embeds']['children']['links']['meta']['total'], 1)
        assert_equal(res.json['data']['embeds']['children']['data'][0]['id'], new_component.forks[0]._id)

    def test_fork_private_node_links(self):
        private_pointer = ProjectFactory(creator=self.user_two)
        actual_pointer = self.private_project.add_pointer(private_pointer, auth=Auth(self.user_two), save=True)

        url = self.private_project_url + '?embed=node_links'

        # Node link is forked, but shows up as a private node link
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        assert_equal(res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node']['errors'][0]['detail'],
                     'You do not have permission to perform this action.')
        assert_equal(res.json['data']['embeds']['node_links']['links']['meta']['total'], 1)

        self.private_project.rm_pointer(actual_pointer, auth=Auth(self.user_two))

    def test_fork_node_links_you_can_access(self):
        pointer = ProjectFactory(creator=self.user)
        self.private_project.add_pointer(pointer, auth=Auth(self.user_two), save=True)

        url = self.private_project_url + '?embed=node_links'

        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        assert_equal(res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node']['data']['id'], pointer._id)
        assert_equal(res.json['data']['embeds']['node_links']['links']['meta']['total'], 1)

    def test_can_fork_registration(self):
        registration = RegistrationFactory(project=self.private_project, user=self.user)

        url = '/{}registrations/{}/forks/'.format(API_BASE, registration._id)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], registration.forks[0]._id)
        assert_equal(res.json['data']['attributes']['title'], 'Fork of ' + registration.title)

    def test_read_only_contributor_can_fork_private_registration(self):
        read_only_user = AuthUserFactory()

        self.private_project.add_contributor(read_only_user, permissions=[permissions.READ], save=True)
        res = self.app.post_json_api(self.private_project_url, self.fork_data, auth=read_only_user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.private_project.forks[0]._id)
        assert_equal(res.json['data']['attributes']['title'], 'Fork of ' + self.private_project.title)
