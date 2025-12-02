
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
    fake_email,
    AuthUserFactory,
    InstitutionFactory,
    NodeFactory,
    PrivateLinkFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)
from website import language
from website.profile.utils import add_contributor_json


from unittest import mock

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from rest_framework import status as http_status

from framework.auth import Auth
from osf.utils import permissions
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    UserFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)
from website import language
from website.profile.utils import add_contributor_json


@pytest.mark.enable_bookmark_creation
class TestProjectContributorViews(OsfTestCase):

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

    def test_cannot_remove_only_visible_contributor(self):
        user1_contrib = self.project.contributor_set.get(user=self.user1)
        user1_contrib.visible = False
        user1_contrib.save()
        url = self.project.api_url_for('project_remove_contributor')
        res = self.app.post(
            url,
            json={
                'contributorID': self.user2._id,
                'nodeIDs': [
                    self.project._id
                ]
            },
            auth=self.auth
        )
        assert res.status_code == http_status.HTTP_403_FORBIDDEN
        assert res.json['message_long'] == 'Must have at least one bibliographic contributor'
        assert self.project.is_contributor(self.user2)

    def test_remove_only_visible_contributor_return_false(self):
        user1_contrib = self.project.contributor_set.get(user=self.user1)
        user1_contrib.visible = False
        user1_contrib.save()
        ret = self.project.remove_contributor(contributor=self.user2, auth=self.consolidate_auth1)
        assert not ret
        assert self.project.is_contributor(self.user2)

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
        assert 'parent project' in res.text

    def test_edit_description(self):
        self.app.post(
            f'/api/v1/project/{self.project._id}/edit/',
            json={'name': 'description', 'value': 'Deep-fried'},
            auth=self.auth
        )
        self.project.reload()
        assert self.project.description == 'Deep-fried'

    def test_project_api_url(self):
        res = self.app.get(
            self.project.api_url,
            auth=self.auth
        )
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

    def test_add_contributor_post(self):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()

        dict2 = add_contributor_json(user2)
        dict3 = add_contributor_json(user3)
        dict2.update(
            {
                'permission': permissions.ADMIN,
                'visible': True,
            }
        )
        dict3.update(
            {
                'permission': permissions.WRITE,
                'visible': False,
            }
        )

        self.app.post(
            f'/api/v1/project/{project._id}/contributors/',
            json={
                'users': [dict2, dict3],
                'node_ids': [project._id],
            },
            content_type='application/json',
            auth=self.auth,
            follow_redirects=True,
        )
        project.reload()
        assert user2 in project.contributors
        # A log event was added
        assert project.logs.latest().action == 'contributor_added'
        assert len(project.contributors) == 3

        assert project.has_permission(user2, permissions.ADMIN) is True
        assert project.has_permission(user2, permissions.WRITE) is True
        assert project.has_permission(user2, permissions.READ) is True

        assert project.has_permission(user3, permissions.ADMIN) is False
        assert project.has_permission(user3, permissions.WRITE) is True
        assert project.has_permission(user3, permissions.READ) is True

    def test_manage_permissions(self):
        resp = self.app.post(
            self.project.api_url + 'contributors/manage/',
            json={
                'contributors': [
                    {
                        'id': self.project.creator._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                    {
                        'id': self.user1._id,
                        'permission': permissions.READ,
                        'registered': True,
                        'visible': True
                    },
                    {
                        'id': self.user2._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                    {
                        'id': self.curator._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': False
                    }
                ]
            },
            auth=self.auth,
        )
        assert resp.status_code == 200

        self.project.reload()

        assert self.project.has_permission(self.user1, permissions.ADMIN) is False
        assert self.project.has_permission(self.user1, permissions.WRITE) is False
        assert self.project.has_permission(self.user1, permissions.READ)

        assert self.project.has_permission(self.user2, permissions.ADMIN) is True
        assert self.project.has_permission(self.user2, permissions.WRITE) is True
        assert self.project.has_permission(self.user2, permissions.READ) is True

        # Test update curator perms
        assert self.project.has_permission(self.curator, permissions.ADMIN)

    def test_manage_permissions_again(self):
        self.app.post(
            self.project.api_url + 'contributors/manage/',
            json={
                'contributors': [
                    {
                        'id': self.user1._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                    {
                        'id': self.user2._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                ]
            },
            auth=self.auth,
        )
        self.project.reload()
        self.app.post(
            self.project.api_url + 'contributors/manage/',
            json={
                'contributors': [
                    {
                        'id': self.user1._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                    {
                        'id': self.user2._id,
                        'permission': permissions.READ,
                        'registered': True,
                        'visible': True
                    },
                ]
            },
            auth=self.auth,
        )

        self.project.reload()

        assert self.project.has_permission(self.user2, permissions.ADMIN) is False
        assert self.project.has_permission(self.user2, permissions.WRITE) is False
        assert self.project.has_permission(self.user2, permissions.READ) is True

        assert self.project.has_permission(self.user1, permissions.ADMIN) is True
        assert self.project.has_permission(self.user1, permissions.WRITE) is True
        assert self.project.has_permission(self.user1, permissions.READ) is True

    def test_contributor_manage_reorder(self):

        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': permissions.ADMIN, 'visible': True},
                {'user': reg_user2, 'permissions': permissions.ADMIN, 'visible': False},
            ]
        )
        # Add a non-registered user
        unregistered_user = project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=self.consolidate_auth1,
            save=True,
        )

        url = project.api_url + 'contributors/manage/'
        self.app.post(
            url,
            json={
                'contributors': [
                    {
                        'id': reg_user2._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': False
                    },
                    {
                        'id': project.creator._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                    {
                        'id': unregistered_user._id,
                        'permission': permissions.ADMIN,
                         'registered': False,
                        'visible': True
                    },
                    {
                        'id': reg_user1._id,
                        'permission': permissions.ADMIN,
                        'registered': True,
                        'visible': True
                    },
                ]
            },
            auth=self.auth,
        )

        project.reload()

        # Note: Cast ForeignList to list for comparison
        assert list(project.contributors) == [reg_user2, project.creator, unregistered_user, reg_user1]

        assert list(project.visible_contributors) == [project.creator, unregistered_user, reg_user1]

    def test_project_remove_contributor(self):
        # User 1 removes user2
        self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.user2._id,
                'nodeIDs': [
                    self.project._id
                ]
            },
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        assert self.user2._id not in self.project.contributors
        # A log event was added
        assert self.project.logs.latest().action == 'contributor_removed'

    def test_project_remove_curator(self):
        """
        When Curators are removed they get a special log message,
        """
        # User 1 removes user2
        self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.curator._id,
                'nodeIDs': [
                    self.project._id
                ]
            },
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        assert self.curator._id not in self.project.contributors
        # A log event was added
        assert self.project.logs.latest().action == 'curator_removed'

    def test_multiple_project_remove_contributor(self):
        # User 1 removes user2
        res = self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.user2._id,
                'nodeIDs': [
                    self.project._id,
                    self.project2._id
                ]
            },
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        self.project2.reload()
        assert self.user2._id not in self.project.contributors
        assert '/dashboard/' not in res.json

        assert self.user2._id not in self.project2.contributors
        # A log event was added
        assert self.project.logs.latest().action == 'contributor_removed'

    def test_private_project_remove_self_not_admin(self):
        # user2 removes self
        res = self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.user2._id,
                'nodeIDs': [
                    self.project._id
                ]
            },
            auth=self.auth2,
            follow_redirects=True
        )
        self.project.reload()
        assert res.status_code == 200
        assert res.json['redirectUrl'] == '/dashboard/'
        assert self.user2._id not in self.project.contributors

    def test_public_project_remove_self_not_admin(self):
        # user2 removes self
        self.public_project = ProjectFactory(creator=self.user1, is_public=True)
        self.public_project.add_contributor(self.user2, auth=Auth(self.user1))
        self.public_project.save()
        res = self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.user2._id,
                'nodeIDs': [
                    self.public_project._id
                ]
            },
            auth=self.auth2
        )
        self.public_project.reload()
        assert res.status_code == 200
        assert res.json['redirectUrl'] == '/' + self.public_project._id + '/'
        assert self.user2._id not in self.public_project.contributors

    def test_project_remove_other_not_admin(self):
        # User 1 removes user2
        res = self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': self.user1._id,
                'nodeIDs': [
                    self.project._id
                ]
            },
            auth=self.auth2
        )
        self.project.reload()
        assert res.status_code == 403
        expected_message = (
                'You do not have permission to perform this action. '
                'If this should not have occurred and the issue persists, '
                + language.SUPPORT_LINK
        )
        assert res.json['message_long'] == expected_message
        assert self.user1 in self.project.contributors

    def test_project_remove_fake_contributor(self):
        # User 1 removes user2
        res = self.app.post(
            self.project.api_url_for('project_remove_contributor'),
            json={
                'contributorID': 'badid',
                'nodeIDs': [self.project._id]
            },
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        # Assert the contributor id was invalid
        assert res.status_code == 400
        assert res.json['message_long'] == 'Contributor not found.'
        assert 'badid' not in self.project.contributors

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

    def test_get_contributors_abbrev(self):
        # create a project with 3 registered contributors
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {
                    'user': reg_user1,
                    'permissions': permissions.ADMIN,
                    'visible': True
                },
                {
                    'user': reg_user2,
                    'permissions': permissions.ADMIN,
                    'visible': True
                },
            ]
        )

        # add an unregistered contributor
        project.add_unregistered_contributor(
            fullname='Jalen Hurts',
            email='gobirds@eagle.fly',
            auth=self.consolidate_auth1,
            save=True,
        )

        res = self.app.get(
            project.api_url_for('get_node_contributors_abbrev'),
            auth=self.auth
        )
        assert len(project.contributors) == 4
        assert len(res.json['contributors']) == 3
        assert len(res.json['others_count']) == 1
        assert res.json['contributors'][0]['separator'] == ','
        assert res.json['contributors'][1]['separator'] == ','
        assert res.json['contributors'][2]['separator'] == ' &'
