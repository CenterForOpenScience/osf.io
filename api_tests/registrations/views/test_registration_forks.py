import pytest
import mock

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from rest_framework import exceptions
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    WithdrawnRegistrationFactory,
    ForkFactory
)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRegistrationForksList:

    @pytest.fixture()
    def pointer(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def private_project(self, user, pointer):
        private_project = ProjectFactory(creator=user)
        private_project.add_pointer(pointer, auth=Auth(user), save=True)
        return private_project

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def private_component(self, user, private_project):
        return NodeFactory(parent=private_project, creator=user)

    @pytest.fixture()
    def public_component(self, user, public_project):
        return NodeFactory(parent=public_project, creator=user, is_public=True)

    @pytest.fixture()
    def private_registration(self, user, private_project, private_component):
        return RegistrationFactory(project=private_project, creator=user)

    @pytest.fixture()
    def public_registration(self, user, public_project, public_component):
        return RegistrationFactory(
            project=public_project,
            creator=user,
            is_public=True)

    @pytest.fixture()
    def private_fork(self, user, private_registration):
        return ForkFactory(project=private_registration, user=user)

    @pytest.fixture()
    def public_fork(self, user, public_registration):
        return ForkFactory(project=public_registration, user=user)

    @pytest.fixture()
    def private_registration_url(self, private_registration):
        return '/{}registrations/{}/forks/'.format(
            API_BASE, private_registration._id)

    @pytest.fixture()
    def public_registration_url(self, public_registration):
        return '/{}registrations/{}/forks/'.format(
            API_BASE, public_registration._id)

    def test_can_access_public_registration_forks_list_when_unauthenticated(
            self, app, public_registration, public_fork, public_registration_url):
        res = app.get(public_registration_url)
        assert len(res.json['data']) == 0
        # Fork defaults to private
        assert not public_fork.is_public

        public_fork.is_public = True
        public_fork.save()

        res = app.get(public_registration_url)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert public_fork.is_public is True
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + \
            public_registration.title
        assert data['id'] == public_fork._id
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_can_access_public_registration_forks_list_authenticated_contributor(
            self, app, user, public_project, public_registration_url, public_fork):
        res = app.get(public_registration_url, auth=user.auth)
        assert res.status_code == 200

        assert not public_fork.is_public
        assert len(res.json['data']) == 1
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + public_project.title
        assert data['id'] == public_fork._id
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_can_access_public_registration_forks_list_authenticated_non_contributor(
            self, app, public_project, public_registration_url, public_fork):
        non_contributor = AuthUserFactory()

        res = app.get(public_registration_url, auth=non_contributor.auth)
        assert res.status_code == 200

        assert len(res.json['data']) == 0
        # Fork defaults to private
        assert not public_fork.is_public

        public_fork.is_public = True
        public_fork.save()

        res = app.get(public_registration_url)
        assert len(res.json['data']) == 1
        assert public_fork.is_public is True
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + public_project.title
        assert data['id'] == public_fork._id
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_authentication(
            self, app, user, private_project, pointer,
            private_registration, private_registration_url,
            private_fork, private_component):

        #   test_cannot_access_private_registration_forks_list_unauthenticated
        res = app.get(private_registration_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_authenticated_contributor_can_access_private_registration_forks_list
        res = app.get('{}?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from'.format(
            private_registration_url), auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + \
            private_project.title
        assert data['id'] == private_fork._id

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert fork_contributors['attributes']['family_name'] == user.family_name
        assert fork_contributors['id'] == user._id

        forked_children = data['embeds']['children']['data'][0]
        assert forked_children['id'] == private_registration.forks.first(
        ).get_nodes(is_node_link=False)[0]._id
        assert forked_children['attributes']['title'] == private_component.title

        forked_node_links = data['embeds']['node_links']['data'][0]['embeds']['target_node']['data']
        assert forked_node_links['id'] == pointer._id
        assert forked_node_links['attributes']['title'] == pointer.title
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

        expected_logs = list(
            private_registration.logs.values_list(
                'action', flat=True))
        expected_logs.append(
            private_registration.nodes[0].logs.latest().action)
        expected_logs.append('node_forked')
        expected_logs.append('node_forked')

        forked_logs = data['embeds']['logs']['data']
        assert set(expected_logs) == set(
            log['attributes']['action'] for log in forked_logs)
        assert len(forked_logs) == len(expected_logs)

        forked_from = data['embeds']['forked_from']['data']
        assert forked_from['id'] == private_registration._id

    #   test_authenticated_non_contributor_cannot_access_private_registration_forks_list
        non_contributor = AuthUserFactory()

        res = app.get(
            private_registration_url,
            auth=non_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail


@pytest.mark.django_db
class TestRegistrationForkCreate:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_pointer(self, user_two):
        return ProjectFactory(creator=user_two)

    @pytest.fixture()
    def private_project(self, user, user_two, private_pointer):
        private_project = ProjectFactory(creator=user)
        private_project.add_pointer(
            private_pointer, auth=Auth(user_two), save=True)
        return private_project

    @pytest.fixture()
    def private_registration(self, user, private_project):
        return RegistrationFactory(creator=user, project=private_project)

    @pytest.fixture()
    def fork_data(self):
        return {
            'data': {
                'type': 'nodes'
            }
        }

    @pytest.fixture()
    def fork_data_with_title(self):
        return {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': 'My Forked Project'
                }
            }
        }

    @pytest.fixture()
    def private_registration_url(self, private_registration):
        return '/{}registrations/{}/forks/'.format(
            API_BASE, private_registration._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_registration(self, user, public_project):
        return RegistrationFactory(
            creator=user,
            project=public_project,
            is_public=True)

    @pytest.fixture()
    def public_registration_url(self, public_registration):
        return '/{}registrations/{}/forks/'.format(
            API_BASE, public_registration._id)

    def test_create_fork_from_public_registration_with_new_title(
            self, app, user, public_registration,
            public_registration_url, fork_data_with_title):
        res = app.post_json_api(
            public_registration_url,
            fork_data_with_title,
            auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == public_registration.forks.first()._id
        assert data['attributes']['title'] == fork_data_with_title['data']['attributes']['title']
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_create_fork_from_private_registration_with_new_title(
            self, app, user, private_registration,
            private_registration_url, fork_data_with_title):
        res = app.post_json_api(
            private_registration_url,
            fork_data_with_title,
            auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == private_registration.forks.first()._id
        assert data['attributes']['title'] == fork_data_with_title['data']['attributes']['title']
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_can_fork_public_registration_logged_in(
            self, app, user_two, public_registration,
            public_registration_url, fork_data):
        res = app.post_json_api(
            public_registration_url,
            fork_data,
            auth=user_two.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == public_registration.forks.first()._id
        assert data['attributes']['title'] == 'Fork of ' + \
            public_registration.title
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_cannot_fork_public_registration_logged_out(
            self, app, public_registration_url, fork_data):
        res = app.post_json_api(
            public_registration_url,
            fork_data,
            expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_can_fork_public_registration_logged_in_contributor(
            self, app, user, public_registration, public_registration_url, fork_data):
        res = app.post_json_api(
            public_registration_url,
            fork_data,
            auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['id'] == public_registration.forks.first()._id
        assert data['attributes']['title'] == 'Fork of ' + \
            public_registration.title
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

    def test_cannot_fork_private_registration_logged_out(
            self, app, private_registration_url, fork_data):
        res = app.post_json_api(
            private_registration_url,
            fork_data,
            expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_cannot_fork_private_registration_logged_in_non_contributor(
            self, app, user_two, private_registration_url, fork_data):
        res = app.post_json_api(
            private_registration_url,
            fork_data, auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_can_fork_private_registration_logged_in_contributor(
            self, app, user, private_registration, private_registration_url, fork_data):
        res = app.post_json_api('{}?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from'.format(
            private_registration_url), fork_data, auth=user.auth)
        assert res.status_code == 201

        data = res.json['data']
        assert data['attributes']['title'] == 'Fork of ' + \
            private_registration.title
        assert not data['attributes']['registration']
        assert data['attributes']['fork'] is True

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert fork_contributors['attributes']['family_name'] == user.family_name
        assert fork_contributors['id'] == user._id

        forked_from = data['embeds']['forked_from']['data']
        assert forked_from['id'] == private_registration._id

    def test_fork_private_components_no_access(
            self, app, user_two, user_three, public_registration,
            public_registration_url, fork_data):
        url = '{}?embed=children'.format(public_registration_url)
        NodeFactory(
            parent=public_registration,
            creator=user_two,
            is_public=False
        )
        res = app.post_json_api(url, fork_data, auth=user_three.auth)
        assert res.status_code == 201
        # Private components that you do not have access to are not forked
        assert res.json['data']['embeds']['children']['links']['meta']['total'] == 0

    def test_fork_components_you_can_access(
            self, app, user, private_registration,
            private_registration_url, fork_data):
        url = '{}?embed=children'.format(private_registration_url)
        new_component = NodeFactory(parent=private_registration, creator=user)
        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['embeds']['children']['links']['meta']['total'] == 1
        assert res.json['data']['embeds']['children']['data'][0]['id'] == new_component.forks.first(
        )._id

    def test_fork_private_node_links(
            self, app, user, private_registration_url, fork_data):

        url = '{}?embed=node_links'.format(private_registration_url)

        # Node link is forked, but shows up as a private node link
        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node'][
            'errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert res.json['data']['embeds']['node_links']['links']['meta']['total'] == 1

    def test_fork_node_links_you_can_access(
            self, app, user, private_project, fork_data):
        pointer = ProjectFactory(creator=user)
        private_project.add_pointer(pointer, auth=Auth(user), save=True)

        new_registration = RegistrationFactory(
            project=private_project, creator=user)

        url = '/{}registrations/{}/forks/{}'.format(
            API_BASE, new_registration._id, '?embed=node_links')

        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.json['data']['embeds']['node_links']['data'][1]['embeds']['target_node']['data']['id'] == pointer._id
        assert res.json['data']['embeds']['node_links']['links']['meta']['total'] == 2

    def test_cannot_fork_retractions(
            self, app, user, private_registration, fork_data):
        with mock.patch('osf.models.AbstractNode.update_search'):
            WithdrawnRegistrationFactory(
                registration=private_registration, user=user)
        url = '/{}registrations/{}/forks/{}'.format(
            API_BASE, private_registration._id, '?embed=forked_from')

        res = app.post_json_api(
            url, fork_data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 403
