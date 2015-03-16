# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from tests.factories import (
    ProjectFactory,
    UserFactory,
    RegistrationFactory,
    NodeFactory,
    NodeLogFactory,
    FolderFactory,
    ExternalAccountFactory,
)
from tests.base import OsfTestCase

from framework.auth import Auth
from framework import utils as framework_utils
from website.profile import utils
from website.project.views.node import (
    _get_summary,
    _serialize_node_search,
    _view_project,
)
from website.serializers.log import LogSerializer
from website.serializers.node import NodeSerializer
from website.serializers.oauth import ExternalAccountSerializer
from website.serializers.user import UserSerializer
from website.util import permissions
from website.views import _render_node
from website.views import serialize_log


class TestNodeSerializers(OsfTestCase):

    # Regression test for #489
    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_get_summary_private_node_should_include_id_and_primary_boolean_reg_and_fork(self):
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

    def test_render_node(self):
        node = ProjectFactory()
        res = _render_node(node)
        assert_equal(res['title'], node.title)
        assert_equal(res['id'], node._primary_key)
        assert_equal(res['url'], node.url)
        assert_equal(res['api_url'], node.api_url)
        assert_equal(res['primary'], node.primary)
        assert_equal(res['date_modified'], framework_utils.iso8601format(node.date_modified))
        assert_equal(res['category'], 'project')

    def test_render_node_returns_permissions(self):
        node = ProjectFactory()
        admin = UserFactory()
        node.add_contributor(admin, auth=Auth(node.creator),
            permissions=permissions.expand_permissions(permissions.ADMIN))
        writer = UserFactory()
        node.add_contributor(writer, auth=Auth(node.creator),
            permissions=permissions.expand_permissions(permissions.WRITE))
        node.save()

        res_admin = _render_node(node, Auth(admin))
        assert_equal(res_admin['permissions'], 'admin')
        res_writer = _render_node(node, Auth(writer))
        assert_equal(res_writer['permissions'], 'write')



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

    def test_serialize_node_search_returns_only_visible_contributors(self):
        node = NodeFactory()
        non_visible_contributor = UserFactory()
        node.add_contributor(non_visible_contributor, visible=False)
        serialized_node = _serialize_node_search(node)

        assert_equal(serialized_node['firstAuthor'], node.visible_contributors[0].family_name)
        assert_equal(len(node.visible_contributors), 1)
        assert_false(serialized_node['etal'])


class TestViewProject(OsfTestCase):

    # related to https://github.com/CenterForOpenScience/openscienceframework.org/issues/1109
    def test_view_project_pointer_count_excludes_folders(self):
        user = UserFactory()
        pointer_project = ProjectFactory(is_public=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        # Project is in a dashboard folder
        folder = FolderFactory(creator=pointed_project.creator)
        folder.add_pointer(pointed_project, Auth(pointed_project.creator), save=True)

        result = _view_project(pointed_project, Auth(pointed_project.creator))
        # pointer_project is included in count, but not folder
        assert_equal(result['node']['points'], 1)


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
        assert_equal(d['date'], framework_utils.iso8601format(log.date))
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


class TestUserSerializer(OsfTestCase):

    # Enumerate all fields that SHOULD be in the export.
    EXPORT_FIELDS = {
        '_id',
        'aka',
        'date_confirmed',
        'date_registered',
        'emails',
        'external_accounts',
        'family_name',
        'fullname',
        'given_name',
        'is_claimed',
        'is_registered',
        'jobs',  # ?
        'merged_by',
        'middle_names',
        'schools',
        'security_messages',  # ?
        'social',
        'suffix',
        'unclaimed_records',  # ?
        'username',
    }

    def setUp(self):
        super(TestUserSerializer, self).setUp()
        self.user = UserFactory()
        self.serializer = UserSerializer(self.user)

    def test_export(self):# Since all expected fields are enumerated, adding new fields will make
        #   this test fail. If the field should be included in an account export
        #   the developer should add it to EXPORT_FIELDS. If it should be
        #   excluded, UserSerializer should be modified.
        assert_equal(
            set(self.serializer.export().keys()),
            self.EXPORT_FIELDS
        )

        expected = {
            k: v
            for k, v in self.user.to_storage().iteritems()
            if k in self.EXPORT_FIELDS
        }

        assert_equal(
            self.serializer.export(),
            expected,
        )

    def test_for_export_external_accounts(self):
        self.user.external_accounts = [
            ExternalAccountFactory(),
            ExternalAccountFactory(),
            ExternalAccountFactory(),
        ]

        # External accounts should use their own serializer
        assert_equal(
            self.serializer.export()['external_accounts'],
            [
                ExternalAccountSerializer(external_account).export()
                for external_account in self.user.external_accounts
            ]
        )


class TestExternalAccountSerializer(OsfTestCase):

    # Enumerate all fields that SHOULD be in the export.
    EXPORT_FIELDS = {
        '_id',
        'provider',
        'provider_id',
        'display_name',
        'profile_url',
        'scopes',
    }

    def setUp(self):
        super(TestExternalAccountSerializer, self).setUp()
        self.external_account = ExternalAccountFactory()

    def test_export(self):
        serializer = ExternalAccountSerializer(self.external_account)

        # Since all expected fields are enumerated, adding new fields will make
        #   this test fail. If the field should be included in an account export
        #   the developer should add it to EXPORT_FIELDS. If it should be
        #   excluded, UserSerializer should be modified.
        assert_equal(
            set(serializer.export().keys()),
            self.EXPORT_FIELDS
        )

        expected = {
            k: v
            for k, v in self.external_account.to_storage().iteritems()
            if k in self.EXPORT_FIELDS
        }

        assert_equal(
            serializer.export(),
            expected,
        )


class TestLogSerializer(OsfTestCase):

    # Enumerate all fields that SHOULD be in the export.
    EXPORT_FIELDS = {
        '_id',
        'action',
        'date',
        'foreign_user',
        'params',
        'user',
    }

    def setUp(self):
        super(TestLogSerializer, self).setUp()
        self.project = ProjectFactory()

    def test_export(self):

        serializer = LogSerializer(self.project.logs[0])

        # Since all expected fields are enumerated, adding new fields will make
        #   this test fail. If the field should be included in an account export
        #   the developer should add it to EXPORT_FIELDS. If it should be
        #   excluded, UserSerializer should be modified.
        assert_equal(
            set(serializer.export().keys()),
            self.EXPORT_FIELDS
        )

        expected = {
            k: v
            for k, v in self.project.logs[0].to_storage().iteritems()
            if k in self.EXPORT_FIELDS
        }

        assert_equal(
            serializer.export(),
            expected,
        )


class TestNodeSerializer(OsfTestCase):

    # Enumerate all fields that SHOULD be in the export.
    EXPORT_FIELDS = {
        '_id',
        'logs',
        'contributors',
        'creator',
        'forked_date',
        'registered_date',
        'comment_level',
        'visible_contributor_ids',
        'title',
        'registered_meta',
        'registered_user',
        'is_registration',
        'category',
        'description',
        'tags',
        'template_node',
        'registered_from',
        'is_public',
        'registered_schema',
        'is_fork',
        'forked_from',
        'date_created',
        'parent_node',  # Derived field
    }

    def setUp(self):
        super(TestNodeSerializer, self).setUp()
        self.project = ProjectFactory()

    def test_export(self):

        serializer = NodeSerializer(self.project)


        import logging
        from pprint import pformat
        logger = logging.getLogger(__name__)
        logger.critical(pformat(serializer.export()))

        # Since all expected fields are enumerated, adding new fields will make
        #   this test fail. If the field should be included in an account export
        #   the developer should add it to EXPORT_FIELDS. If it should be
        #   excluded, UserSerializer should be modified.
        assert_equal(
            set(serializer.export().keys()),
            self.EXPORT_FIELDS
        )

        expected = {
            k: v
            for k, v in self.project.to_storage().iteritems()
            if k in self.EXPORT_FIELDS
        }
        # Added fields, not in to_storage()
        parent_node = self.project.parent_node
        expected['parent_node'] = parent_node._id if parent_node else None

        expected['logs'] = [
            LogSerializer(log).export()
            for log in self.project.logs
        ]

        assert_equal(
            serializer.export(),
            expected,
        )

    # TODO: Test parent_node not None