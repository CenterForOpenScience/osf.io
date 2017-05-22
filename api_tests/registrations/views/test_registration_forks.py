import pytest
import mock

from framework.auth.core import Auth
from website.models import Node
from website.util import permissions
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    WithdrawnRegistrationFactory,
    ForkFactory
)


@pytest.mark.django_db
class TestRegistrationForksList(object):

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)
        self.private_project.save()
        self.component = NodeFactory(parent=self.private_project, creator=self.user)
        self.pointer = ProjectFactory(creator=self.user)
        self.private_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_registration = RegistrationFactory(project=self.private_project, creator=self.user)
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
        assert len(res.json['data']) == 0
        # Fork defaults to private
        assert self.public_fork.is_public == False

        self.public_fork.is_public = True
        self.public_fork.save()

        res = self.app.get(self.public_registration_url)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert self.public_fork.is_public == True
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + self.public_registration.title
        assert data['id'] == self.public_fork._id
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_can_access_public_registration_forks_list_authenticated_contributor(self):
        res = self.app.get(self.public_registration_url, auth=self.user.auth)
        assert res.status_code == 200

        assert self.public_fork.is_public == False
        assert len(res.json['data']) == 1
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + self.public_project.title
        assert data['id'] == self.public_fork._id
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_can_access_public_registration_forks_list_authenticated_non_contributor(self):
        res = self.app.get(self.public_registration_url, auth=self.user_two.auth)
        assert res.status_code == 200

        assert len(res.json['data']) == 0
        # Fork defaults to private
        assert self.public_fork.is_public == False

        self.public_fork.is_public = True
        self.public_fork.save()

        res = self.app.get(self.public_registration_url)
        assert len(res.json['data']) == 1
        assert self.public_fork.is_public == True
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + self.public_project.title
        assert data['id'] == self.public_fork._id
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_cannot_access_private_registration_forks_list_unauthenticated(self):
        res = self.app.get(self.private_registration_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

    def test_authenticated_contributor_can_access_private_registration_forks_list(self):
        res = self.app.get(self.private_registration_url + '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from', auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + self.private_project.title
        assert data['id'] == self.private_fork._id

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert fork_contributors['attributes']['family_name'] == self.user.family_name
        assert fork_contributors['id'] == self.user._id

        forked_children = data['embeds']['children']['data'][0]
        assert forked_children['id'] == self.private_registration.forks.first().nodes[0]._id
        assert forked_children['attributes']['title'] == self.component.title

        forked_node_links = data['embeds']['node_links']['data'][0]['embeds']['target_node']['data']
        assert forked_node_links['id'] == self.pointer._id
        assert forked_node_links['attributes']['title'] == self.pointer.title
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

        expected_logs = list(self.private_registration.logs.values_list('action', flat=True))
        expected_logs.append(self.private_registration.nodes[0].logs.latest().action)
        expected_logs.append('node_forked')
        expected_logs.append('node_forked')

        forked_logs = data['embeds']['logs']['data']
        assert set(expected_logs) == set(log['attributes']['action'] for log in forked_logs)
        assert len(forked_logs) == len(expected_logs)

        forked_from = data['embeds']['forked_from']['data']
        assert forked_from['id'] == self.private_registration._id

    def test_authenticated_non_contributor_cannot_access_private_registration_forks_list(self):
        res = self.app.get(self.private_registration_url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

@pytest.mark.django_db
class TestRegistrationForkCreate(object):

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
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

    def test_create_fork_from_public_registration_with_new_title(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data_with_title, auth=self.user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == self.public_registration.forks.first()._id
        assert data['attributes']['title'] == self.fork_data_with_title['data']['attributes']['title']
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_create_fork_from_private_registration_with_new_title(self):
        res = self.app.post_json_api(self.private_registration_url, self.fork_data_with_title, auth=self.user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == self.private_registration.forks.first()._id
        assert data['attributes']['title'] == self.fork_data_with_title['data']['attributes']['title']
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_can_fork_public_registration_logged_in(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data, auth=self.user_two.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == self.public_registration.forks.first()._id
        assert data['attributes']['title'] == 'Fork of ' + self.public_registration.title
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_cannot_fork_public_registration_logged_out(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

    def test_can_fork_public_registration_logged_in_contributor(self):
        res = self.app.post_json_api(self.public_registration_url, self.fork_data, auth=self.user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == self.public_registration.forks.first()._id
        assert data['attributes']['title'] == 'Fork of ' + self.public_registration.title
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

    def test_cannot_fork_private_registration_logged_out(self):
        res = self.app.post_json_api(self.private_registration_url, self.fork_data, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

    def test_cannot_fork_private_registration_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.private_registration_url, self.fork_data, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_can_fork_private_registration_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_registration_url + '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from', self.fork_data, auth=self.user.auth)
        assert res.status_code == 201

        data = res.json['data']
        assert data['attributes']['title'] == 'Fork of ' + self.private_registration.title
        assert data['attributes']['registration'] == False
        assert data['attributes']['fork'] == True

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert fork_contributors['attributes']['family_name'] == self.user.family_name
        assert fork_contributors['id'] == self.user._id

        forked_from = data['embeds']['forked_from']['data']
        assert forked_from['id'] == self.private_registration._id

    def test_fork_private_components_no_access(self):
        url = self.public_registration_url + '?embed=children'
        private_component = NodeFactory(parent=self.public_registration, creator=self.user_two, is_public=False)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user_three.auth)
        assert res.status_code == 201
        # Private components that you do not have access to are not forked
        assert res.json['data']['embeds']['children']['links']['meta']['total'] == 0

    def test_fork_components_you_can_access(self):
        url = self.private_registration_url + '?embed=children'
        new_component = NodeFactory(parent=self.private_registration, creator=self.user)
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert res.status_code == 201
        assert res.json['data']['embeds']['children']['links']['meta']['total'] == 1
        assert res.json['data']['embeds']['children']['data'][0]['id'] == new_component.forks.first()._id

    def test_fork_private_node_links(self):

        url = self.private_registration_url + '?embed=node_links'

        # Node link is forked, but shows up as a private node link
        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node']['errors'][0]['detail'] == 'You do not have permission to perform this action.'
        assert res.json['data']['embeds']['node_links']['links']['meta']['total'] == 1

    def test_fork_node_links_you_can_access(self):
        pointer = ProjectFactory(creator=self.user)
        self.private_project.add_pointer(pointer, auth=Auth(self.user), save=True)

        new_registration = RegistrationFactory(project = self.private_project, creator=self.user)

        url = '/{}registrations/{}/forks/'.format(API_BASE, new_registration._id) + '?embed=node_links'

        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth)
        assert res.json['data']['embeds']['node_links']['data'][1]['embeds']['target_node']['data']['id'] == pointer._id
        assert res.json['data']['embeds']['node_links']['links']['meta']['total'] == 2

    def test_cannot_fork_retractions(self):
        with mock.patch('osf.models.AbstractNode.update_search'):
            retraction = WithdrawnRegistrationFactory(registration=self.private_registration, user=self.user)
        url = '/{}registrations/{}/forks/'.format(API_BASE, self.private_registration._id) + '?embed=forked_from'

        res = self.app.post_json_api(url, self.fork_data, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 403
