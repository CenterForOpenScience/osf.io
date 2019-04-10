import pytest
import mock

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    ForkFactory
)
from rest_framework import exceptions
from website import mails
from osf.utils import permissions

from api.nodes.serializers import NodeForksSerializer


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeForksList:

    @pytest.fixture()
    def pointer(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def private_project(self, user, pointer):
        private_project = ProjectFactory()
        private_project.add_contributor(
            user, permissions=[permissions.READ, permissions.WRITE])
        private_project.add_pointer(pointer, auth=Auth(user), save=True)
        private_project.save()
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
    def private_fork(self, user, private_project):
        return ForkFactory(project=private_project, user=user)

    @pytest.fixture()
    def public_fork(self, user, public_project):
        return ForkFactory(project=public_project, user=user)

    @pytest.fixture()
    def private_project_url(self, private_project):
        return '/{}nodes/{}/forks/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project_url(self, public_project):
        return '/{}nodes/{}/forks/'.format(API_BASE, public_project._id)

    def test_can_access_public_node_forks_list_when_unauthenticated(
            self, app, public_project, public_fork, public_project_url):
        res = app.get(public_project_url)
        assert res.status_code == 200
        assert len(res.json['data']) == 0
        # Fork defaults to private
        assert not public_fork.is_public

        public_fork.is_public = True
        public_fork.save()

        res = app.get(public_project_url)
        assert len(res.json['data']) == 1
        assert public_fork.is_public
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + public_project.title
        assert data['id'] == public_fork._id
        assert not data['attributes']['registration']
        assert data['attributes']['fork']

    def test_can_access_public_node_forks_list_authenticated_contributor(
            self, app, user, public_project, public_fork, public_project_url):
        res = app.get(public_project_url, auth=user.auth)
        assert res.status_code == 200
        assert not public_fork.is_public
        assert len(res.json['data']) == 1
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + public_project.title
        assert data['id'] == public_fork._id
        assert not data['attributes']['registration']
        assert data['attributes']['fork']

    def test_can_access_public_node_forks_list_authenticated_non_contributor(
            self, app, public_project, public_fork, public_project_url):
        non_contrib = AuthUserFactory()
        res = app.get(public_project_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0
        # Fork defaults to private
        assert not public_fork.is_public

        public_fork.is_public = True
        public_fork.save()

        res = app.get(public_project_url)
        assert len(res.json['data']) == 1
        assert public_fork.is_public
        data = res.json['data'][0]
        assert data['attributes']['title'] == 'Fork of ' + public_project.title
        assert data['id'] == public_fork._id
        assert not data['attributes']['registration']
        assert data['attributes']['fork']

    def test_authenticated_contributor_can_access_private_node_forks_list(
            self, app, user, private_project, private_component,
            private_fork, pointer, private_project_url):
        res = app.get(
            private_project_url +
            '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from',
            auth=user.auth)
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
        assert forked_children['id'] == private_component.forks.first()._id
        assert forked_children['attributes']['title'] == private_component.title

        forked_node_links = data['embeds']['node_links']['data'][0]['embeds']['target_node']['data']
        assert forked_node_links['id'] == pointer._id
        assert forked_node_links['attributes']['title'] == pointer.title

        auth = Auth(user)
        expected_logs = list(
            private_project.get_aggregate_logs_queryset(
                auth
            ).values_list('action', flat=True)
        )
        expected_logs.append('node_forked')

        forked_logs = data['embeds']['logs']['data']
        forked_log_actions = [
            log['attributes']['action']for log in forked_logs
        ]
        assert set(expected_logs) == set(forked_log_actions)
        assert len(set(forked_log_actions)) == len(set(expected_logs))

        forked_from = data['embeds']['forked_from']['data']
        assert forked_from['id'] == private_project._id

    def test_node_forks_list_errors(self, app, private_project_url):

        #   test_cannot_access_private_node_forks_list_unauthenticated
        res = app.get(private_project_url, expect_errors=True)

        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_authenticated_non_contributor_cannot_access_private_node_forks_list
        non_contrib = AuthUserFactory()
        res = app.get(
            private_project_url,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_forks_list_does_not_show_registrations_of_forks(
            self, app, user, public_project, public_fork, public_project_url):
        reg = RegistrationFactory(project=public_fork, is_public=True)

        # confirm registration shows up in node forks
        assert reg in public_project.forks.all()
        assert len(public_project.forks.all()) == 2
        res = app.get(public_project_url, auth=user.auth)

        # confirm registration of fork does not show up in public data (only public_fork)
        assert len(res.json['data']) == 1

        public_fork.is_deleted = True
        public_fork.save()

        # confirm it's still a fork even after deletion
        assert len(public_project.forks.all()) == 2

        # confirm fork no longer shows on public project's forks list
        res = app.get(public_project_url, auth=user.auth)
        assert len(res.json['data']) == 0


@pytest.mark.django_db
class TestNodeForkCreate:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def private_project_url(self, private_project):
        return '/{}nodes/{}/forks/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project_url(self, public_project):
        return '/{}nodes/{}/forks/'.format(API_BASE, public_project._id)

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
                'attributes':
                    {'title': 'My Forked Project'}
            }
        }

    def test_create_fork_from_public_project_with_new_title(
            self, app, user, public_project, fork_data_with_title, public_project_url):
        res = app.post_json_api(
            public_project_url,
            fork_data_with_title,
            auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == public_project.forks.first()._id
        assert res.json['data']['attributes']['title'] == fork_data_with_title['data']['attributes']['title']

    def test_create_fork_from_private_project_with_new_title(
            self, app, user, private_project, fork_data_with_title, private_project_url):
        res = app.post_json_api(
            private_project_url,
            fork_data_with_title,
            auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == private_project.forks.first()._id
        assert res.json['data']['attributes']['title'] == fork_data_with_title['data']['attributes']['title']

    def test_can_fork_public_node_logged_in(
            self, app, public_project, fork_data, public_project_url):
        non_contrib = AuthUserFactory()
        res = app.post_json_api(
            public_project_url,
            fork_data,
            auth=non_contrib.auth)
        fork = public_project.forks.first()
        assert res.status_code == 201
        assert res.json['data']['id'] == fork._id
        assert res.json['data']['attributes']['title'] == 'Fork of ' + \
            public_project.title
        assert public_project.logs.latest().date and fork.last_logged

    def test_cannot_fork_errors(
            self, app, fork_data, public_project_url,
            private_project_url):

        #   test_cannot_fork_public_node_logged_out
        res = app.post_json_api(
            public_project_url, fork_data,
            expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_cannot_fork_private_node_logged_out
        res = app.post_json_api(
            private_project_url, fork_data,
            expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_cannot_fork_private_node_logged_in_non_contributor
        non_contrib = AuthUserFactory()
        res = app.post_json_api(
            private_project_url, fork_data,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_can_fork_public_node_logged_in_contributor(
            self, app, user, public_project, fork_data, public_project_url):
        res = app.post_json_api(public_project_url, fork_data, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == public_project.forks.first()._id
        assert res.json['data']['attributes']['title'] == 'Fork of ' + \
            public_project.title

    def test_can_fork_private_node_logged_in_contributor(
            self, app, user, private_project, fork_data, private_project_url):
        res = app.post_json_api(
            private_project_url +
            '?embed=children&embed=node_links&embed=logs&embed=contributors&embed=forked_from',
            fork_data, auth=user.auth)
        assert res.status_code == 201

        data = res.json['data']
        assert data['attributes']['title'] == 'Fork of ' + \
            private_project.title

        fork_contributors = data['embeds']['contributors']['data'][0]['embeds']['users']['data']
        assert fork_contributors['attributes']['family_name'] == user.family_name
        assert fork_contributors['id'] == user._id

        forked_from = data['embeds']['forked_from']['data']
        assert forked_from['id'] == private_project._id

    def test_fork_private_components_no_access(
            self, app, user_two, public_project,
            fork_data, public_project_url):
        user_three = AuthUserFactory()
        url = public_project_url + '?embed=children'
        NodeFactory(
            parent=public_project,
            creator=user_two,
            is_public=False
        )
        res = app.post_json_api(url, fork_data, auth=user_three.auth)
        assert res.status_code == 201
        # Private components that you do not have access to are not forked
        assert res.json['data']['embeds']['children']['links']['meta']['total'] == 0

    def test_fork_components_you_can_access(
            self, app, user, private_project,
            fork_data, private_project_url):
        url = private_project_url + '?embed=children'
        new_component = NodeFactory(parent=private_project, creator=user)
        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['embeds']['children']['links']['meta']['total'] == 1
        assert res.json['data']['embeds']['children']['data'][0]['id'] == new_component.forks.first(
        )._id
        assert res.json['data']['embeds']['children']['data'][0]['attributes']['title'] == new_component.title

    def test_fork_private_node_links(
            self, app, user, user_two, private_project,
            fork_data, private_project_url):
        private_pointer = ProjectFactory(creator=user_two)
        actual_pointer = private_project.add_pointer(
            private_pointer, auth=Auth(user_two), save=True)

        url = private_project_url + '?embed=node_links'

        # Node link is forked, but shows up as a private node link
        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.status_code == 201

        assert (res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node']
                ['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail)
        assert res.json['data']['embeds']['node_links']['links']['meta']['total'] == 1

        private_project.rm_pointer(actual_pointer, auth=Auth(user_two))

    def test_fork_node_links_you_can_access(
            self, app, user, user_two, private_project,
            fork_data, private_project_url):
        pointer = ProjectFactory(creator=user)
        private_project.add_pointer(pointer, auth=Auth(user_two), save=True)

        url = private_project_url + '?embed=node_links'

        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.status_code == 201

        assert res.json['data']['embeds']['node_links']['data'][0]['embeds']['target_node']['data']['id'] == pointer._id
        assert res.json['data']['embeds']['node_links']['links']['meta']['total'] == 1

    def test_can_fork_registration(
            self, app, user, private_project, fork_data):
        registration = RegistrationFactory(project=private_project, user=user)

        url = '/{}registrations/{}/forks/'.format(API_BASE, registration._id)
        res = app.post_json_api(url, fork_data, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == registration.forks.first()._id
        assert res.json['data']['attributes']['title'] == 'Fork of ' + \
            registration.title

    def test_read_only_contributor_can_fork_private_registration(
            self, app, private_project, fork_data, private_project_url):
        read_contrib = AuthUserFactory()

        private_project.add_contributor(
            read_contrib,
            permissions=[permissions.READ], save=True)
        res = app.post_json_api(
            private_project_url, fork_data,
            auth=read_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == private_project.forks.first()._id
        assert res.json['data']['attributes']['title'] == 'Fork of ' + \
            private_project.title

    def test_send_email_success(
            self, app, user, public_project_url,
            fork_data_with_title, public_project):

        with mock.patch.object(mails, 'send_mail', return_value=None) as mock_send_mail:
            res = app.post_json_api(
                public_project_url,
                fork_data_with_title,
                auth=user.auth)
            assert res.status_code == 201
            assert res.json['data']['id'] == public_project.forks.first()._id
            mock_send_mail.assert_called_with(
                user.email,
                mails.FORK_COMPLETED,
                title=public_project.title,
                guid=res.json['data']['id'],
                mimetype='html',
                can_change_preferences=False)

    def test_send_email_failed(
            self, app, user, public_project_url,
            fork_data_with_title, public_project):

        with mock.patch.object(NodeForksSerializer, 'save', side_effect=Exception()):
            with mock.patch.object(mails, 'send_mail', return_value=None) as mock_send_mail:
                with pytest.raises(Exception):
                    app.post_json_api(
                        public_project_url,
                        fork_data_with_title,
                        auth=user.auth)
                    mock_send_mail.assert_called_with(
                        user.email,
                        mails.FORK_FAILED,
                        title=public_project.title,
                        guid=public_project._id,
                        mimetype='html',
                        can_change_preferences=False)
