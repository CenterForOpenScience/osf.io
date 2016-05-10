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
    RetractedRegistrationFactory,
    ForkFactory
)


class TestRegistrationForksList(ApiTestCase):
    def setUp(self):
        super(TestRegistrationForksList, self).setUp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory()
        self.private_project.add_contributor(self.user, permissions=[permissions.READ, permissions.WRITE])
        self.private_project.save()
        self.component = NodeFactory(parent=self.private_project, creator=self.user)
        self.pointer = ProjectFactory(creator=self.user)
        self.private_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_registration = RegistrationFactory(project = self.private_project, creator=self.user)
        self.private_fork = ForkFactory(project=self.private_registration, user=self.user)
        self.private_registration_url = '/{}registrations/{}/forks/'.format(API_BASE, self.private_registration._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.save()
        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(project = self.public_project, creator=self.user, is_public=True)

        self.public_registration_url = '/{}registrations/{}/forks/'.format(API_BASE, self.public_registration._id)
        self.public_fork = ForkFactory(project=self.public_registration, user=self.user)
        self.user_two = AuthUserFactory()

    def test_can_access_public_registration_forks_list_when_unauthenticated(self):
        res = self.app.get(self.public_registration_url)
        assert_equal(len(res.json['data']), 0)
        # Fork defaults to private
        assert_equal(self.public_fork.is_public, False)

        self.public_fork.is_public = True
        self.public_fork.save()

        res = self.app.get(self.public_registration_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(self.public_fork.is_public, True)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_registration.title)
        assert_equal(data['id'], self.public_fork._id)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_can_access_public_registration_forks_list_authenticated_contributor(self):
        res = self.app.get(self.public_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        assert_equal(self.public_fork.is_public, False)
        assert_equal(len(res.json['data']), 1)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_project.title)
        assert_equal(data['id'], self.public_fork._id)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_can_access_public_registration_forks_list_authenticated_non_contributor(self):
        res = self.app.get(self.public_registration_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)

        assert_equal(len(res.json['data']), 0)
        # Fork defaults to private
        assert_equal(self.public_fork.is_public, False)

        self.public_fork.is_public = True
        self.public_fork.save()

        res = self.app.get(self.public_registration_url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(self.public_fork.is_public, True)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_project.title)
        assert_equal(data['id'], self.public_fork._id)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_cannot_access_private_registration_forks_list_unauthenticated(self):
        res = self.app.get(self.private_registration_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_authenticated_contributor_can_access_private_registration_forks_list(self):
        res = self.app.get(self.private_registration_url + '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from', auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        data = res.json['data'][0]
        assert_equal(data['attributes']['title'], 'Fork of ' + self.private_project.title)
        assert_equal(data['id'], self.private_fork._id)

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert_equal(fork_contributors['attributes']['family_name'], self.user.family_name)
        assert_equal(fork_contributors['id'], self.user._id)

        forked_children = data['embeds']['children']['data'][0]
        assert_equal(forked_children['id'], self.private_registration.nodes[0].forks[0]._id)
        assert_equal(forked_children['attributes']['title'], self.component.title)

        forked_node_links = data['embeds']['node_links']['data'][0]['embeds']['target_node']['data']
        assert_equal(forked_node_links['id'], self.pointer._id)
        assert_equal(forked_node_links['attributes']['title'], self.pointer.title)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

        expected_logs = [log.action for log in self.private_registration.logs]
        expected_logs.append(self.private_registration.nodes[0].logs[0].action)
        expected_logs.append('node_forked')
        expected_logs.append('node_forked')

        forked_logs = data['embeds']['logs']['data']
        assert_equal(set(expected_logs), set(log['attributes']['action'] for log in forked_logs))
        assert_equal(len(forked_logs), 6)

        forked_from = data['embeds']['forked_from']['data']
        assert_equal(forked_from['id'], self.private_registration._id)

    def test_authenticated_non_contributor_cannot_access_private_registration_forks_list(self):
        res = self.app.get(self.private_registration_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')


class TestRegistrationForkCreate(ApiTestCase):

    def setUp(self):
        super(TestRegistrationForkCreate, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)

        private_pointer = ProjectFactory(creator=self.user_two)
        actual_pointer = self.private_project.add_pointer(private_pointer, auth=Auth(self.user_two), save=True)

        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)

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

        self.private_registration_url = '/{}registrations/{}/forks/'.format(API_BASE, self.private_registration._id)


        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project, is_public=True)
        self.public_registration_url = '/{}registrations/{}/forks/'.format(API_BASE, self.public_registration._id)

    def tearDown(self):
        super(TestRegistrationForkCreate, self).tearDown()
        Node.remove()

    def test_create_fork_from_public_registration_with_new_title(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data_with_title, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(data['id'], self.public_registration.forks[0]._id)
        assert_equal(data['attributes']['title'], self.fork_data_with_title['data']['attributes']['title'])
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_create_fork_from_private_registration_with_new_title(self):
        res = self.app.post_json_api(self.private_registration_url, self.fork_data_with_title, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(data['id'], self.private_registration.forks[0]._id)
        assert_equal(data['attributes']['title'], self.fork_data_with_title['data']['attributes']['title'])
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_can_fork_public_registration_logged_in(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data, auth=self.user_two.auth)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(data['id'], self.public_registration.forks[0]._id)
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_registration.title)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_cannot_fork_public_registration_logged_out(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_can_fork_public_registration_logged_in_contributor(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        data = res.json['data']
        assert_equal(data['id'], self.public_registration.forks[0]._id)
        assert_equal(data['attributes']['title'], 'Fork of ' + self.public_registration.title)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

    def test_cannot_fork_private_registration_logged_out(self):
        res = self.app.post_json_api(self.private_registration_url, self.fork_data, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_cannot_fork_private_registration_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.private_registration_url, self.fork_data, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_can_fork_private_registration_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_registration_url + '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from', self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        data = res.json['data']
        assert_equal(data['attributes']['title'], 'Fork of ' + self.private_registration.title)
        assert_equal(data['attributes']['registration'], False)
        assert_equal(data['attributes']['fork'], True)

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert_equal(fork_contributors['attributes']['family_name'], self.user.family_name)
        assert_equal(fork_contributors['id'], self.user._id)

        forked_from = data['embeds']['forked_from']['data']
        assert_equal(forked_from['id'], self.private_registration._id)

    def test_fork_private_components_no_access(self):
        url = self.public_registration_url + '?embed=children'
        private_component = NodeFactory(parent=self.public_registration, creator=self.user_two, is_public=False)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user_three.auth)
        assert_equal(res.status_code, 201)
        # Private components that you do not have access to are not forked
        assert_equal(res.json['data']['embeds']['children']['links']['meta']['total'], 0)

    def test_fork_components_you_can_access(self):
        url = self.private_registration_url + '?embed=children'
        new_component = NodeFactory(parent=self.private_registration, creator=self.user)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['embeds']['children']['links']['meta']['total'], 1)
        assert_equal(res.json['data']['embeds']['children']['data'][0]['id'], new_component.forks[0]._id)

    def test_fork_private_node_links(self):

        url = self.private_registration_url + '?embed=node_links'

        # Node link is forked, but shows up as a private node link
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node']['errors'][0]['detail'],
                     'You do not have permission to perform this action.')
        assert_equal(res.json['data']['embeds']['node_links']['links']['meta']['total'], 1)

    def test_fork_node_links_you_can_access(self):
        pointer = ProjectFactory(creator=self.user)
        self.private_project.add_pointer(pointer, auth=Auth(self.user), save=True)

        new_registration = RegistrationFactory(project = self.private_project, creator=self.user)

        url = '/{}registrations/{}/forks/'.format(API_BASE, new_registration._id) + '?embed=node_links'

        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert_equal(res.json['data']['embeds']['node_links']['data'][1]['embeds']['target_node']['data']['id'], pointer._id)
        assert_equal(res.json['data']['embeds']['node_links']['links']['meta']['total'], 2)

    def test_cannot_fork_retractions(self):
        retraction = RetractedRegistrationFactory(registration=self.private_registration, user=self.user)
        url = '/{}registrations/{}/forks/'.format(API_BASE, self.private_registration._id) + '?embed=forked_from'

        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
