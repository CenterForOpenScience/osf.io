# -*- coding: utf-8 -*-

import mock
import datetime as dt
from nose.tools import *  # noqa (PEP8 asserts)

import pytest
from osf_tests.factories import (
    ProjectFactory,
    UserFactory,
    RegistrationFactory,
    NodeFactory,
    CollectionFactory,
)
from osf.models import NodeRelation
from osf.utils import permissions
from tests.base import OsfTestCase, get_default_metaschema

from framework.auth import Auth
from website.project.views.node import _view_project, _serialize_node_search, _get_children, _get_readable_descendants
from website.views import serialize_node_summary
from website.profile import utils
from website import filters, settings

pytestmark = pytest.mark.django_db

@pytest.mark.enable_bookmark_creation
class TestUserSerializers(OsfTestCase):

    @pytest.mark.enable_quickfiles_creation
    def test_serialize_user(self):
        master = UserFactory()
        user = UserFactory()
        master.merge_user(user)
        d = utils.serialize_user(user)
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d.get('username', None), None)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime('%Y-%m-%d'))
        assert_equal(d['active'], user.is_active)

    @pytest.mark.enable_quickfiles_creation
    def test_serialize_user_merged(self):
        master = UserFactory()
        user = UserFactory()
        master.merge_user(user)
        d = utils.serialize_user(user, full=True)
        assert_true(d['is_merged'])
        assert_equal(d['merged_by']['url'], user.merged_by.url)
        assert_equal(d['merged_by']['absolute_url'], user.merged_by.absolute_url)

    def test_serialize_user_full(self):
        user = UserFactory()
        project = ProjectFactory(creator=user, is_public=False)
        NodeFactory(creator=user)
        ProjectFactory(creator=user, is_public=True)
        CollectionFactory(creator=user)
        RegistrationFactory(project=project)
        d = utils.serialize_user(user, full=True, include_node_counts=True)
        profile_image_url = filters.profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                                                  user,
                                                  use_ssl=True,
                                                  size=settings.PROFILE_IMAGE_LARGE)
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d.get('username'), None)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['profile_image_url'], profile_image_url)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime('%Y-%m-%d'))
        projects = [
            node
            for node in user.contributed
            if node.category == 'project'
            and not node.is_registration
            and not node.is_deleted
        ]
        public_projects = [p for p in projects if p.is_public]
        assert_equal(d['number_projects'], len(projects))
        assert_equal(d['number_public_projects'], len(public_projects))


@pytest.mark.enable_bookmark_creation
class TestNodeSerializers(OsfTestCase):

    # Regression test for #489
    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_serialize_node_summary_private_node_should_include_id_and_primary_boolean_reg_and_fork(self):
        user = UserFactory()
        # user cannot see this node
        node = ProjectFactory(is_public=False)
        result = serialize_node_summary(
            node, auth=Auth(user),
            primary=True,
        )

        # serialized result should have id and primary
        assert_equal(result['id'], node._primary_key)
        assert_true(result['primary'], True)
        assert_equal(result['is_registration'], node.is_registration)
        assert_equal(result['is_fork'], node.is_fork)

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/668
    def test_serialize_node_summary_for_registration_uses_correct_date_format(self):
        reg = RegistrationFactory()
        res = serialize_node_summary(reg, auth=Auth(reg.creator))
        assert_equal(res['registered_date'],
                reg.registered_date.strftime('%Y-%m-%d %H:%M UTC'))

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/858
    def test_serialize_node_summary_private_registration_should_include_is_registration(self):
        user = UserFactory()
        # non-contributor cannot see private registration of public project
        node = ProjectFactory(is_public=True)
        reg = RegistrationFactory(project=node, user=node.creator)
        res = serialize_node_summary(reg, auth=Auth(user))

        # serialized result should have is_registration
        assert_true(res['is_registration'])

    # https://openscience.atlassian.net/browse/OSF-4618
    def test_get_children_only_returns_child_nodes_with_admin_permissions(self):
        user = UserFactory()
        admin_project = ProjectFactory()
        admin_project.add_contributor(user, auth=Auth(admin_project.creator),
                                      permissions=permissions.expand_permissions(permissions.ADMIN))
        admin_project.save()

        admin_component = NodeFactory(parent=admin_project)
        admin_component.add_contributor(user, auth=Auth(admin_component.creator),
                                        permissions=permissions.expand_permissions(permissions.ADMIN))
        admin_component.save()

        read_and_write = NodeFactory(parent=admin_project)
        read_and_write.add_contributor(user, auth=Auth(read_and_write.creator),
                                       permissions=permissions.expand_permissions(permissions.WRITE))
        read_and_write.save()
        read_only = NodeFactory(parent=admin_project)
        read_only.add_contributor(user, auth=Auth(read_only.creator),
                                  permissions=permissions.expand_permissions(permissions.READ))
        read_only.save()

        non_contributor = NodeFactory(parent=admin_project)
        components = _get_children(admin_project, Auth(user))
        assert_equal(len(components), 1)

    def test_serialize_node_summary_private_fork_should_include_is_fork(self):
        user = UserFactory()
        # non-contributor cannot see private fork of public project
        node = ProjectFactory(is_public=True)
        consolidated_auth = Auth(user=node.creator)
        fork = node.fork_node(consolidated_auth)

        res = serialize_node_summary(
            fork, auth=Auth(user),
            primary=True,
        )
        # serialized result should have is_fork
        assert_true(res['is_fork'])

    def test_serialize_node_summary_private_fork_private_project_should_include_is_fork(self):
        # contributor on a private project
        user = UserFactory()
        node = ProjectFactory(is_public=False)
        node.add_contributor(user)

        # contributor cannot see private fork of this project
        consolidated_auth = Auth(user=node.creator)
        fork = node.fork_node(consolidated_auth)

        res = serialize_node_summary(
            fork, auth=Auth(user),
            primary=True,
        )
        # serialized result should have is_fork
        assert_false(res['can_view'])
        assert_true(res['is_fork'])

    def test_serialize_node_summary_child_exists(self):
        user = UserFactory()
        parent_node = ProjectFactory(creator=user)
        linked_node = ProjectFactory(creator=user)
        result = _view_project(parent_node, Auth(user))
        assert_equal(result['node']['child_exists'], False)
        parent_node.add_node_link(linked_node, Auth(user), save=True)
        result = _view_project(parent_node, Auth(user))
        assert_equal(result['node']['child_exists'], False)
        child_component = NodeFactory(creator=user, parent=parent_node)
        result = _view_project(parent_node, Auth(user))
        assert_equal(result['node']['child_exists'], True)

    def test_serialize_node_search_returns_only_visible_contributors(self):
        node = NodeFactory()
        non_visible_contributor = UserFactory()
        node.add_contributor(non_visible_contributor, visible=False)
        serialized_node = _serialize_node_search(node)

        assert_equal(serialized_node['firstAuthor'], node.visible_contributors[0].family_name)
        assert_equal(len(node.visible_contributors), 1)
        assert_false(serialized_node['etal'])


@pytest.mark.enable_bookmark_creation
class TestViewProject(OsfTestCase):

    def setUp(self):
        super(TestViewProject, self).setUp()
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_view_project_pending_registration_for_admin_contributor_does_contain_cancel_link(self):
        pending_reg = RegistrationFactory(project=self.node, archive=True)
        assert_true(pending_reg.is_pending_registration)
        result = _view_project(pending_reg, Auth(self.user))

        assert_not_equal(result['node']['disapproval_link'], '')
        assert_in('/?token=', result['node']['disapproval_link'])
        pending_reg.delete()

    def test_view_project_pending_registration_for_write_contributor_does_not_contain_cancel_link(self):
        write_user = UserFactory()
        self.node.add_contributor(write_user, permissions=permissions.WRITE,
                                  auth=Auth(self.user), save=True)
        pending_reg = RegistrationFactory(project=self.node, archive=True)
        assert_true(pending_reg.is_pending_registration)
        result = _view_project(pending_reg, Auth(write_user))

        assert_equal(result['node']['disapproval_link'], '')
        pending_reg.delete()

    def test_view_project_child_exists(self):
        linked_node = ProjectFactory(creator=self.user)
        result = _view_project(self.node, Auth(self.user))
        assert_equal(result['node']['child_exists'], False)
        self.node.add_node_link(linked_node, Auth(self.user), save=True)
        result = _view_project(self.node, Auth(self.user))
        assert_equal(result['node']['child_exists'], False)
        child_component = NodeFactory(creator=self.user, parent=self.node)
        result = _view_project(self.node, Auth(self.user))
        assert_equal(result['node']['child_exists'], True)



@pytest.mark.enable_bookmark_creation
class TestViewProjectEmbeds(OsfTestCase):

    def setUp(self):
        super(TestViewProjectEmbeds, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_view_project_embed_forks_excludes_registrations(self):
        project = ProjectFactory()
        fork = project.fork_node(Auth(project.creator))
        reg = RegistrationFactory(project=fork)

        res = _view_project(project, auth=Auth(project.creator), embed_forks=True)

        assert_in('forks', res['node'])
        assert_equal(len(res['node']['forks']), 1)

        assert_equal(res['node']['forks'][0]['id'], fork._id)

    # Regression test
    def test_view_project_embed_registrations_sorted_by_registered_date_descending(self):
        # register a project several times, with various registered_dates
        registrations = []
        for days_ago in (21, 3, 2, 8, 13, 5, 1):
            registration = RegistrationFactory(project=self.project)
            reg_date = registration.registered_date - dt.timedelta(days_ago)
            registration.registered_date = reg_date
            registration.save()
            registrations.append(registration)

        registrations.sort(key=lambda r: r.registered_date, reverse=True)
        expected = [r._id for r in registrations]

        data = _view_project(node=self.project, auth=Auth(self.project.creator), embed_registrations=True)
        actual = [n['id'] for n in data['node']['registrations']]
        assert_equal(actual, expected)

    def test_view_project_embed_descendants(self):
        child = NodeFactory(parent=self.project, creator=self.user)
        res = _view_project(self.project, auth=Auth(self.project.creator), embed_descendants=True)
        assert_in('descendants', res['node'])
        assert_equal(len(res['node']['descendants']), 1)
        assert_equal(res['node']['descendants'][0]['id'], child._id)


class TestGetReadableDescendants(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()

    def test__get_readable_descendants(self):
        project = ProjectFactory(creator=self.user)
        child = NodeFactory(parent=project, creator=self.user)
        nodes, all_readable = _get_readable_descendants(auth=Auth(project.creator), node=project)
        assert_equal(nodes[0]._id, child._id)
        assert_true(all_readable)

    def test__get_readable_descendants_includes_pointers(self):
        project = ProjectFactory(creator=self.user)
        pointed = ProjectFactory()
        node_relation = project.add_pointer(pointed, auth=Auth(self.user))
        project.save()

        nodes, all_readable = _get_readable_descendants(auth=Auth(project.creator), node=project)

        assert_equal(len(nodes), 1)
        assert_equal(nodes[0].title, pointed.title)
        assert_equal(nodes[0]._id, pointed._id)
        assert_true(all_readable)

    def test__get_readable_descendants_masked_by_permissions(self):
        # Users should be able to see through components they do not have
        # permissions to.
        # Users should not be able to see through links to nodes they do not
        # have permissions to.
        #
        #                   1(AB)
        #                  /  |  \
        #                 *   |   \
        #                /    |    \
        #             2(A)  4(B)    7(A)
        #               |     |     |    \
        #               |     |     |     \
        #             3(AB) 5(B)    8(AB) 9(B)
        #                     |
        #                     |
        #                   6(A)
        #
        #
        userA = UserFactory(fullname='User A')
        userB = UserFactory(fullname='User B')

        project1 = ProjectFactory(creator=self.user, title='One')
        project1.add_contributor(userA, auth=Auth(self.user), permissions=['read'])
        project1.add_contributor(userB, auth=Auth(self.user), permissions=['read'])

        component2 = ProjectFactory(creator=self.user, title='Two')
        component2.add_contributor(userA, auth=Auth(self.user), permissions=['read'])

        component3 = ProjectFactory(creator=self.user, title='Three')
        component3.add_contributor(userA, auth=Auth(self.user), permissions=['read'])
        component3.add_contributor(userB, auth=Auth(self.user), permissions=['read'])

        component4 = ProjectFactory(creator=self.user, title='Four')
        component4.add_contributor(userB, auth=Auth(self.user), permissions=['read'])

        component5 = ProjectFactory(creator=self.user, title='Five')
        component5.add_contributor(userB, auth=Auth(self.user), permissions=['read'])

        component6 = ProjectFactory(creator=self.user, title='Six')
        component6.add_contributor(userA, auth=Auth(self.user), permissions=['read'])

        component7 = ProjectFactory(creator=self.user, title='Seven')
        component7.add_contributor(userA, auth=Auth(self.user), permissions=['read'])

        component8 = ProjectFactory(creator=self.user, title='Eight')
        component8.add_contributor(userA, auth=Auth(self.user), permissions=['read'])
        component8.add_contributor(userB, auth=Auth(self.user), permissions=['read'])

        component9 = ProjectFactory(creator=self.user, title='Nine')
        component9.add_contributor(userB, auth=Auth(self.user), permissions=['read'])

        project1.add_pointer(component2, Auth(self.user))
        NodeRelation.objects.create(parent=project1, child=component4)
        NodeRelation.objects.create(parent=project1, child=component7)
        NodeRelation.objects.create(parent=component2, child=component3)
        NodeRelation.objects.create(parent=component4, child=component5)
        NodeRelation.objects.create(parent=component5, child=component6)
        NodeRelation.objects.create(parent=component7, child=component8)
        NodeRelation.objects.create(parent=component7, child=component9)

        nodes, all_readable = _get_readable_descendants(auth=Auth(userA), node=project1)
        assert_equal(len(nodes), 3)
        assert_false(all_readable)

        for node in nodes:
            assert_in(node.title, ['Two', 'Six', 'Seven'])

        nodes, all_readable = _get_readable_descendants(auth=Auth(userB), node=project1)
        assert_equal(len(nodes), 3)
        assert_false(all_readable)
        for node in nodes:
            assert_in(node.title, ['Four', 'Eight', 'Nine'])


class TestNodeLogSerializers(OsfTestCase):

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
            'title': 'Lover Boy',
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
        assert_in('secure.gravatar.com', user_info['profile_image_url'])
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
        assert_in('secure.gravatar.com', user_info['profile_image_url'])
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
        assert_in('secure.gravatar.com', user_info['profile_image_url'])
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
        assert_in('secure.gravatar.com', user_info['profile_image_url'])
        assert_equal(user_info['profile_url'], self.profile)
