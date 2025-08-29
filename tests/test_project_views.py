
from unittest import mock

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status as http_status

from api_tests.utils import create_test_file
from framework.auth import Auth
from osf.models import NodeLog
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    NodeFactory,
    PrivateLinkFactory,
    ProjectFactory,
    RegistrationFactory,
)
from tests.base import OsfTestCase
from tests.utils import capture_notifications


@pytest.mark.enable_bookmark_creation
class TestProjectViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user1 = AuthUserFactory()
        self.user1.save()
        self.consolidate_auth1 = Auth(user=self.user1)
        self.auth = self.user1.auth
        self.user2 = AuthUserFactory()
        self.curator = AuthUserFactory()
        self.auth2 = self.user2.auth
        # A project has 2 contributors
        self.project = ProjectFactory(
            title='Ham',
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.add_contributor(
            self.curator,
            auth=Auth(self.curator),
            permissions='write',
            visible=False,
            make_curator=True
        )
        self.project.save()

        self.project2 = ProjectFactory(
            title='Tofu',
            description='Glazed',
            creator=self.user1
        )
        self.project2.add_contributor(self.user2, auth=Auth(self.user1))

        self.project2.save()

    @mock.patch('framework.status.push_status_message')
    def test_view_project_tos_status_message(self, mock_push_status_message):
        self.app.get(
            self.project.web_url_for('view_project'),
            auth=self.auth
        )
        assert mock_push_status_message.called
        assert 'terms_of_service' == mock_push_status_message.mock_calls[0][2]['id']

    @mock.patch('framework.status.push_status_message')
    def test_view_project_no_tos_status_message(self, mock_push_status_message):
        self.user1.accepted_terms_of_service = timezone.now()
        self.user1.save()
        self.app.get(
            self.project.web_url_for('view_project'),
            auth=self.auth
        )
        assert not mock_push_status_message.called

    def test_node_setting_with_multiple_matched_institution_email_domains(self):
        # User has alternate emails matching more than one institution's email domains
        inst1 = InstitutionFactory(email_domains=['foo.bar'])
        inst2 = InstitutionFactory(email_domains=['baz.qux'])

        user = AuthUserFactory()
        user.emails.create(address='queen@foo.bar')
        user.emails.create(address='brian@baz.qux')
        user.save()
        project = ProjectFactory(creator=user)

        # node settings page loads without error
        url = project.web_url_for('node_setting')
        res = self.app.get(url, auth=user.auth)
        assert res.status_code == 200

        # user is automatically affiliated with institutions
        # that matched email domains
        user.reload()
        assert inst1 in user.get_affiliated_institutions()
        assert inst2 in user.get_affiliated_institutions()

    def test_edit_title_empty(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('edit_node')
        res = self.app.post(url, json={'name': 'title', 'value': ''}, auth=self.user1.auth)
        assert res.status_code == 400
        assert 'Title cannot be blank' in res.text

    def test_edit_title_invalid(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('edit_node')
        res = self.app.post(url, json={'name': 'title', 'value': '<a></a>'}, auth=self.user1.auth)
        assert res.status_code == 400
        assert 'Invalid title.' in res.text

    def test_view_project_doesnt_select_for_update(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('view_project')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            res = self.app.get(url, auth=self.user1.auth)

        for_update_sql = connection.ops.for_update_sql()
        assert res.status_code == 200
        assert not any(for_update_sql in query['sql'] for query in ctx.captured_queries)

    def test_can_view_nested_project_as_admin(self):
        self.parent_project = NodeFactory(
            title='parent project',
            category='project',
            parent=self.project,
            is_public=False
        )
        self.parent_project.save()
        self.child_project = NodeFactory(
            title='child project',
            category='project',
            parent=self.parent_project,
            is_public=False
        )
        self.child_project.save()
        url = self.child_project.web_url_for('view_project')
        res = self.app.get(url, auth=self.auth)
        assert 'Private Project' not in res.text
        assert 'parent project'in res.text

    def test_edit_description(self):
        self.app.post(
            f'/api/v1/project/{self.project._id}/edit/',
            json={'name': 'description', 'value': 'Deep-fried'},
            auth=self.auth
        )
        self.project.reload()
        assert self.project.description == 'Deep-fried'

    def test_project_api_url(self):
        url = self.project.api_url
        res = self.app.get(url, auth=self.auth)
        data = res.json
        assert data['node']['category'] == 'Project'
        assert data['node']['node_type'] == 'project'

        assert data['node']['title'] == self.project.title
        assert data['node']['is_public'] == self.project.is_public
        assert data['node']['is_registration'] == False
        assert data['node']['id'] == self.project._primary_key
        assert data['user']['is_contributor']
        assert data['node']['description'] == self.project.description
        assert data['node']['url'] == self.project.url
        assert data['node']['tags'] == list(self.project.tags.values_list('name', flat=True))
        assert 'forked_date' in data['node']
        assert 'registered_from_url' in data['node']
        # TODO: Test "parent" and "user" output

    def test_project_remove_self_only_admin(self):
        # User 1 removes user2
        res = self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.user1._id,
                'nodeIDs': [
                    self.project._id
                ]
            },
            auth=self.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert res.status_code == 400
        assert res.json['message_long'] == 'Could not remove contributor.'
        assert self.user1 in self.project.contributors

    def test_edit_node_title(self):
        # The title is changed though posting form data
        self.app.post(
            f'/api/v1/project/{self.project._id}/edit/',
            json={
                'name': 'title',
                'value': 'Bacon'
            },
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        # The title was changed
        assert self.project.title == 'Bacon'
        # A log event was saved
        assert self.project.logs.latest().action == 'edit_title'

    def test_add_tag(self):
        self.app.post(
            self.project.api_url_for('project_add_tag'),
            json={
                'tag': "foo'ta#@%#%^&g?"
            },
            auth=self.auth
        )
        self.project.reload()
        assert "foo'ta#@%#%^&g?" in self.project.tags.values_list('name', flat=True)
        assert "foo'ta#@%#%^&g?" == self.project.logs.latest().params['tag']

    def test_remove_tag(self):
        self.project.add_tag("foo'ta#@%#%^&g?", auth=self.consolidate_auth1, save=True)
        assert "foo'ta#@%#%^&g?" in self.project.tags.values_list('name', flat=True)
        url = self.project.api_url_for('project_remove_tag')
        self.app.delete(url, json={'tag': "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert "foo'ta#@%#%^&g?" not in self.project.tags.values_list('name', flat=True)
        latest_log = self.project.logs.latest()
        assert 'tag_removed' == latest_log.action
        assert "foo'ta#@%#%^&g?" == latest_log.params['tag']

    # Regression test for #OSF-5257
    def test_removal_empty_tag_throws_error(self):
        url = self.project.api_url_for('project_remove_tag')
        res = self.app.delete(url, json={'tag': ''}, auth=self.auth)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    # Regression test for #OSF-5257
    def test_removal_unknown_tag_throws_error(self):
        self.project.add_tag('narf', auth=self.consolidate_auth1, save=True)
        url = self.project.api_url_for('project_remove_tag')
        res = self.app.delete(url, json={'tag': 'troz'}, auth=self.auth)
        assert res.status_code == http_status.HTTP_409_CONFLICT

    def test_suspended_project(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        node.remove_node(Auth(self.user1))
        node.reload()
        node.suspended = True
        node.save()
        url = node.api_url
        res = self.app.get(url)
        assert res.status_code == 451

    def test_private_link_edit_name(self):
        link = PrivateLinkFactory(name='link')
        link.nodes.add(self.project)
        link.save()
        assert link.name == 'link'
        url = self.project.api_url + 'private_link/edit/'
        self.app.put(
            url,
            json={'pk': link._id, 'value': 'new name'},
            auth=self.auth, follow_redirects=True)
        self.project.reload()
        link.reload()
        assert link.name == 'new name'

    def test_remove_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete(
            url,
            json={'private_link_id': link._id},
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        link.reload()
        assert link.is_deleted

    def test_remove_private_link_log(self):
        link = PrivateLinkFactory()
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete(
            url,
            json={'private_link_id': link._id},
            auth=self.auth,
            follow_redirects=True
        )

        last_log = self.project.logs.latest()
        assert last_log.action == NodeLog.VIEW_ONLY_LINK_REMOVED
        assert not last_log.params.get('anonymous_link')

    def test_remove_private_link_anonymous_log(self):
        link = PrivateLinkFactory(anonymous=True)
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete(
            url,
            json={'private_link_id': link._id},
            auth=self.auth,
            follow_redirects=True
        )

        last_log = self.project.logs.latest()
        assert last_log.action == NodeLog.VIEW_ONLY_LINK_REMOVED
        assert last_log.params.get('anonymous_link')

    def test_remove_component(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        url = node.api_url
        res = self.app.delete(url, json={}, auth=self.auth, follow_redirects=True)
        node.reload()
        assert node.is_deleted == True
        assert 'url' in res.json
        assert res.json['url'] == self.project.url

    def test_cant_remove_component_if_not_admin(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        non_admin = AuthUserFactory()
        node.add_contributor(
            non_admin,
            permissions=permissions.WRITE,
            save=True,
        )

        url = node.api_url
        res = self.app.delete(url, json={}, auth=non_admin.auth, follow_redirects=True)

        assert res.status_code == http_status.HTTP_403_FORBIDDEN
        assert not node.is_deleted

    def test_view_project_returns_whether_to_show_wiki_widget(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user, is_public=True)
        project.add_contributor(user)
        project.save()

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'show_wiki_widget' in res.json['user']

    def test_fork_grandcomponents_has_correct_root(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        child = NodeFactory(parent=project, creator=user)
        grand_child = NodeFactory(parent=child, creator=user)
        project.save()

        fork = project.fork_node(auth)
        fork.save()
        grand_child_fork = fork.nodes[0].nodes[0]
        assert grand_child_fork.root == fork

    def test_fork_count_does_not_include_deleted_forks(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        with capture_notifications():
            fork = project.fork_node(auth)
        project.save()
        fork.remove_node(auth)

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert 'fork_count' in res.json['node']
        assert 0 == res.json['node']['fork_count']

    def test_fork_count_does_not_include_fork_registrations(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        with capture_notifications():
            fork = project.fork_node(auth)
        project.save()
        registration = RegistrationFactory(project=fork)

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert 'fork_count'in res.json['node']
        assert 1 == res.json['node']['fork_count']

    def test_registration_retraction_redirect(self):
        url = self.project.web_url_for('node_registration_retraction_redirect')
        res = self.app.get(url, auth=self.auth)
        assert res.status_code == 302
        assert self.project.web_url_for('node_registration_retraction_get', _guid=True) in res.location

    def test_update_node(self):
        url = self.project.api_url_for('update_node')
        res = self.app.put(url, json={'title': 'newtitle'}, auth=self.auth)
        assert res.status_code == 200
        self.project.reload()
        assert self.project.title == 'newtitle'

    # Regression test
    def test_update_node_with_tags(self):
        self.project.add_tag('cheezebørger', auth=Auth(self.project.creator), save=True)
        url = self.project.api_url_for('update_node')
        res = self.app.put(url, json={'title': 'newtitle'}, auth=self.auth)
        assert res.status_code == 200
        self.project.reload()
        assert self.project.title == 'newtitle'

    # Regression test
    def test_retraction_view(self):
        project = ProjectFactory(creator=self.user1, is_public=True)

        registration = RegistrationFactory(project=project, is_public=True)
        reg_file = create_test_file(registration, user=registration.creator, create_guid=True)
        registration.retract_registration(self.user1)

        approval_token = registration.retraction.approval_state[self.user1._id]['approval_token']
        registration.retraction.approve_retraction(self.user1, approval_token)
        registration.save()

        url = registration.web_url_for('view_project')
        res = self.app.get(url, auth=self.auth)

        assert 'Mako Runtime Error' not in res.text
        assert registration.title in res.text
        assert res.status_code == 200

        for route in ['files', 'wiki/home', 'contributors', 'settings', 'withdraw', 'register', 'register/fakeid']:
            res = self.app.get(f'{url}{route}/', auth=self.auth)
            assert res.status_code == 302, route
            res = self.app.get(f'{url}{route}/', auth=self.auth, follow_redirects=True)
            assert res.status_code == 200, route
            assert 'This project is a withdrawn registration of' in res.text, route

        res = self.app.get(f'/{reg_file.guids.first()._id}/')
        assert res.status_code == 200
        assert 'This project is a withdrawn registration of' in res.text