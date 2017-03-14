# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import datetime
import random
import string
import unittest

import mock
import pytz
from dateutil import parser
from django.utils import timezone
from framework.auth import Auth
from framework.celery_tasks import handlers
from framework.exceptions import PermissionsError
from framework.sessions import set_session
from modularodm import Q
#from modularodm.exceptions import ValidationError, ValidationValueError
from osf.exceptions import ValidationError, ValidationValueError
from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import (OsfTestCase, fake,
                        get_default_metaschema)
from tests.factories import (AuthUserFactory, InstitutionFactory, NodeFactory,
                             NodeLicenseRecordFactory, NodeLogFactory,
                             NodeWikiFactory, PointerFactory,
                             PrivateLinkFactory, ProjectFactory,
                             ProjectWithAddonFactory, RegistrationFactory,
                             SessionFactory, UnconfirmedUserFactory,
                             UnregUserFactory, UserFactory, WatchConfigFactory)
from tests.utils import mock_archive
from website import language, settings
from addons.wiki.models import NodeWikiPage
from website.exceptions import NodeStateError, TagNotFoundError
from website.project.model import (DraftRegistration, MetaSchema, Node,
                                   NodeLog, Pointer, ensure_schemas,
                                   get_pointer_parent, has_anonymous_link)
from website.project.spam.model import SpamStatus
from website.project.tasks import on_node_updated
from website.util.permissions import ADMIN, CREATOR_PERMISSIONS, READ, WRITE

GUID_FACTORIES = UserFactory, NodeFactory, ProjectFactory


class TestAddonCallbacks(OsfTestCase):
    """Verify that callback functions are called at the right times, with the
    right arguments.
    """
    callbacks = {
        'after_remove_contributor': None,
        'after_set_privacy': None,
        'after_fork': (None, None),
        'after_register': (None, None),
    }

    def setUp(self):
        def mock_get_addon(addon_name, deleted=False):
            # Overrides AddonModelMixin.get_addon -- without backrefs,
            # no longer guaranteed to return the same set of objects-in-memory
            return self.patched_addons.get(addon_name, None)

        super(TestAddonCallbacks, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.parent = ProjectFactory()
        self.node = NodeFactory(creator=self.user, project=self.parent)
        self.patches = []
        self.patched_addons = {}
        self.original_get_addon = Node.get_addon

        # Mock addon callbacks
        for addon in self.node.addons:
            mock_settings = mock.create_autospec(addon.__class__)
            for callback, return_value in self.callbacks.iteritems():
                mock_callback = getattr(mock_settings, callback)
                mock_callback.return_value = return_value
                patch = mock.patch.object(
                    addon,
                    callback,
                    getattr(mock_settings, callback)
                )
                patch.start()
                self.patches.append(patch)
            self.patched_addons[addon.config.short_name] = addon
        n_patch = mock.patch.object(
            self.node,
            'get_addon',
            mock_get_addon
        )
        n_patch.start()
        self.patches.append(n_patch)

    def tearDown(self):
        super(TestAddonCallbacks, self).tearDown()
        for patcher in self.patches:
            patcher.stop()

    def test_remove_contributor_callback(self):
        user2 = UserFactory()
        self.node.add_contributor(contributor=user2, auth=self.auth)
        self.node.remove_contributor(contributor=user2, auth=self.auth)
        for addon in self.node.addons:
            callback = addon.after_remove_contributor
            callback.assert_called_once_with(
                self.node, user2, self.auth
            )

    def test_set_privacy_callback(self):
        self.node.set_privacy('public', self.auth)
        for addon in self.node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                self.node, 'public',
            )

        self.node.set_privacy('private', self.auth)
        for addon in self.node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                self.node, 'private'
            )

    def test_fork_callback(self):
        fork = self.node.fork_node(auth=self.auth)
        for addon in self.node.addons:
            callback = addon.after_fork
            callback.assert_called_once_with(
                self.node, fork, self.user
            )

    def test_register_callback(self):
        with mock_archive(self.node) as registration:
            for addon in self.node.addons:
                callback = addon.after_register
                callback.assert_called_once_with(
                    self.node, registration, self.user
                )


class TestRoot(OsfTestCase):
    def setUp(self):
        super(TestRoot, self).setUp()
        # Create project
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user, description='foobar')

        self.registration = RegistrationFactory(project=self.project)

    def test_top_level_project_has_own_root(self):
        assert_equal(self.project.root._id, self.project._id)

    def test_child_project_has_root_of_parent(self):
        child = NodeFactory(parent=self.project)
        assert_equal(child.root._id, self.project._id)
        assert_equal(child.root._id, self.project.root._id)

    def test_grandchild_root_relationships(self):
        child_node_one = NodeFactory(parent=self.project)
        child_node_two = NodeFactory(parent=self.project)
        grandchild_from_one = NodeFactory(parent=child_node_one)
        grandchild_from_two = NodeFactory(parent=child_node_two)

        assert_equal(child_node_one.root._id, child_node_two.root._id)
        assert_equal(grandchild_from_one.root._id, grandchild_from_two.root._id)
        assert_equal(grandchild_from_two.root._id, self.project.root._id)

    def test_grandchild_has_root_of_immediate_parent(self):
        child_node = NodeFactory(parent=self.project)
        grandchild_node = NodeFactory(parent=child_node)
        assert_equal(child_node.root._id, grandchild_node.root._id)

    def test_registration_has_own_root(self):
        assert_equal(self.registration.root._id, self.registration._id)

    def test_registration_children_have_correct_root(self):
        registration_child = NodeFactory(parent=self.registration)
        assert_equal(registration_child.root._id, self.registration._id)

    def test_registration_grandchildren_have_correct_root(self):
        registration_child = NodeFactory(parent=self.registration)
        registration_grandchild = NodeFactory(parent=registration_child)

        assert_equal(registration_grandchild.root._id, self.registration._id)

    def test_fork_has_own_root(self):
        fork = self.project.fork_node(auth=self.auth)
        fork.save()
        assert_equal(fork.root._id, fork._id)

    def test_fork_children_have_correct_root(self):
        fork = self.project.fork_node(auth=self.auth)
        fork_child = NodeFactory(parent=fork)
        assert_equal(fork_child.root._id, fork._id)

    def test_fork_grandchildren_have_correct_root(self):
        fork = self.project.fork_node(auth=self.auth)
        fork_child = NodeFactory(parent=fork)
        fork_grandchild = NodeFactory(parent=fork_child)
        assert_equal(fork_grandchild.root._id, fork._id)

    def test_template_project_has_own_root(self):
        new_project = self.project.use_as_template(auth=self.auth)
        assert_equal(new_project.root._id, new_project._id)

    def test_template_project_child_has_correct_root(self):
        new_project = self.project.use_as_template(auth=self.auth)
        new_project_child = NodeFactory(parent=new_project)
        assert_equal(new_project_child.root._id, new_project._id)

    def test_template_project_grandchild_has_correct_root(self):
        new_project = self.project.use_as_template(auth=self.auth)
        new_project_child = NodeFactory(parent=new_project)
        new_project_grandchild = NodeFactory(parent=new_project_child)
        assert_equal(new_project_grandchild.root._id, new_project._id)

    def test_node_find_returns_correct_nodes(self):
        # Build up a family of nodes
        child_node_one = NodeFactory(parent=self.project)
        child_node_two = NodeFactory(parent=self.project)
        NodeFactory(parent=child_node_one)
        NodeFactory(parent=child_node_two)
        # Create a rogue node that's not related at all
        NodeFactory()

        family_ids = [self.project._id] + [r._id for r in self.project.get_descendants_recursive()]
        family_nodes = Node.find(Q('root', 'eq', self.project._id))
        number_of_nodes = family_nodes.count()

        assert_equal(number_of_nodes, 5)
        found_ids = []
        for node in family_nodes:
            assert_in(node._id, family_ids)
            found_ids.append(node._id)
        for node_id in family_ids:
            assert_in(node_id, found_ids)

    def test_get_descendants_recursive_returns_in_depth_order(self):
        """Test the get_descendants_recursive function to make sure its
        not returning any new nodes that we're not expecting
        """
        child_node_one = NodeFactory(parent=self.project)
        child_node_two = NodeFactory(parent=self.project)
        NodeFactory(parent=child_node_one)
        NodeFactory(parent=child_node_two)

        parent_list = [self.project._id]
        # Verifies, for every node in the list, that parent, we've seen before, in order.
        for project in self.project.get_descendants_recursive():
            parent_list.append(project._id)
            if project.parent:
                assert_in(project.parent._id, parent_list)


class TestTemplateNode(OsfTestCase):

    def setUp(self):
        super(TestTemplateNode, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _verify_log(self, node):
        """Tests to see that the "created from" log event is present (alone).

        :param node: A node having been created from a template just prior
        """
        assert_equal(len(node.logs), 1)
        assert_equal(node.logs[0].action, NodeLog.CREATED_FROM)

    def test_simple_template(self):
        """Create a templated node, with no changes"""
        # created templated node
        new = self.project.use_as_template(
            auth=self.auth
        )

        assert_equal(new.title, self._default_title(self.project))
        assert_not_equal(new.date_created, self.project.date_created)
        self._verify_log(new)

    def test_simple_template_title_changed(self):
        """Create a templated node, with the title changed"""
        changed_title = 'Made from template'

        # create templated node
        new = self.project.use_as_template(
            auth=self.auth,
            changes={
                self.project._primary_key: {
                    'title': changed_title,
                }
            }
        )

        assert_equal(new.title, changed_title)
        assert_not_equal(new.date_created, self.project.date_created)
        self._verify_log(new)

    def test_use_as_template_preserves_license(self):
        license = NodeLicenseRecordFactory()
        self.project.node_license = license
        self.project.save()
        new = self.project.use_as_template(
            auth=self.auth
        )

        assert_equal(new.license.node_license._id, license.node_license._id)
        self._verify_log(new)

    def _create_complex(self):
        # create project connected via Pointer
        self.pointee = ProjectFactory(creator=self.user)
        self.project.add_pointer(self.pointee, auth=self.auth)

        # create direct children
        self.component = NodeFactory(creator=self.user, parent=self.project)
        self.subproject = ProjectFactory(creator=self.user, parent=self.project)

    @staticmethod
    def _default_title(x):
        if isinstance(x, Node):
            return str(language.TEMPLATED_FROM_PREFIX + x.title)
        return str(x.title)

    def test_complex_template(self):
        """Create a templated node from a node with children"""
        self._create_complex()

        # create templated node
        new = self.project.use_as_template(auth=self.auth)

        assert_equal(new.title, self._default_title(self.project))
        assert_equal(len(new.nodes), len(self.project.nodes))
        # check that all children were copied
        assert_equal(
            [x.title for x in new.nodes],
            [x.title for x in self.project.nodes],
        )
        # ensure all child nodes were actually copied, instead of moved
        assert {x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in self.project.nodes}
        )

    def test_complex_template_titles_changed(self):
        self._create_complex()

        # build changes dict to change each node's title
        changes = {
            x._primary_key: {
                'title': 'New Title ' + str(idx)
            } for idx, x in enumerate(self.project.nodes)
        }

        # create templated node
        new = self.project.use_as_template(
            auth=self.auth,
            changes=changes
        )

        for old_node, new_node in zip(self.project.nodes, new.nodes):
            if isinstance(old_node, Node):
                assert_equal(
                    changes[old_node._primary_key]['title'],
                    new_node.title,
                )
            else:
                assert_equal(
                    old_node.title,
                    new_node.title,
                )

    def test_template_wiki_pages_not_copied(self):
        self.project.update_node_wiki(
            'template', 'lol',
            auth=self.auth
        )
        new = self.project.use_as_template(
            auth=self.auth
        )
        assert_in('template', self.project.wiki_pages_current)
        assert_in('template', self.project.wiki_pages_versions)
        assert_equal(new.wiki_pages_current, {})
        assert_equal(new.wiki_pages_versions, {})

    def test_user_who_makes_node_from_template_has_creator_permission(self):
        project = ProjectFactory(is_public=True)
        user = UserFactory()
        auth = Auth(user)

        templated = project.use_as_template(auth)

        assert_equal(templated.get_permissions(user), ['read', 'write', 'admin'])

    def test_template_security(self):
        """Create a templated node from a node with public and private children

        Children for which the user has no access should not be copied
        """
        other_user = UserFactory()
        other_user_auth = Auth(user=other_user)

        self._create_complex()

        # set two projects to public - leaving self.component as private
        self.project.is_public = True
        self.project.save()
        self.subproject.is_public = True
        self.subproject.save()

        # add new children, for which the user has each level of access
        self.read = NodeFactory(creator=self.user, parent=self.project)
        self.read.add_contributor(other_user, permissions=['read', ])
        self.read.save()

        self.write = NodeFactory(creator=self.user, parent=self.project)
        self.write.add_contributor(other_user, permissions=['read', 'write'])
        self.write.save()

        self.admin = NodeFactory(creator=self.user, parent=self.project)
        self.admin.add_contributor(other_user)
        self.admin.save()

        # filter down self.nodes to only include projects the user can see
        visible_nodes = filter(
            lambda x: x.can_view(other_user_auth),
            self.project.nodes
        )

        # create templated node
        new = self.project.use_as_template(auth=other_user_auth)

        assert_equal(new.title, self._default_title(self.project))

        # check that all children were copied
        assert_equal(
            set(x.template_node._id for x in new.nodes),
            set(x._id for x in visible_nodes),
        )
        # ensure all child nodes were actually copied, instead of moved
        assert_true({x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in self.project.nodes}
        ))

        # ensure that the creator is admin for each node copied
        for node in new.nodes:
            assert_equal(
                node.permissions.get(other_user._id),
                ['read', 'write', 'admin'],
            )


class TestForkNode(OsfTestCase):

    def setUp(self):
        super(TestForkNode, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _cmp_fork_original(self, fork_user, fork_date, fork, original,
                           title_prepend='Fork of '):
        """Compare forked node with original node. Verify copied fields,
        modified fields, and files; recursively compare child nodes.

        :param fork_user: User who forked the original nodes
        :param fork_date: Datetime (UTC) at which the original node was forked
        :param fork: Forked node
        :param original: Original node
        :param title_prepend: String prepended to fork title

        """
        # Test copied fields
        assert_equal(title_prepend + original.title, fork.title)
        assert_equal(original.category, fork.category)
        assert_equal(original.description, fork.description)
        assert_true(len(fork.logs) == len(original.logs) + 1)
        assert_not_equal(original.logs.latest().action, NodeLog.NODE_FORKED)
        assert_equal(fork.logs.latest().action, NodeLog.NODE_FORKED)
        assert_equal(original.tags, fork.tags)
        assert_equal(original.parent_node is None, fork.parent_node is None)

        # Test modified fields
        assert_true(fork.is_fork)
        assert_equal(len(fork.private_links), 0)
        assert_equal(fork.forked_from, original)
        assert_in(fork._id, [n._id for n in original.forks])
        # Note: Must cast ForeignList to list for comparison
        assert_equal(list(fork.contributors), [fork_user])
        assert_true((fork_date - fork.date_created) < datetime.timedelta(seconds=30))
        assert_not_equal(fork.forked_date, original.date_created)

        # Test that pointers were copied correctly
        assert_equal(
            [pointer.node for pointer in original.nodes_pointer],
            [pointer.node for pointer in fork.nodes_pointer],
        )

        # Test that add-ons were copied correctly
        assert_equal(
            original.get_addon_names(),
            fork.get_addon_names()
        )
        assert_equal(
            [addon.config.short_name for addon in original.get_addons()],
            [addon.config.short_name for addon in fork.get_addons()]
        )

        fork_user_auth = Auth(user=fork_user)
        # Recursively compare children
        for idx, child in enumerate(original.nodes):
            if child.can_view(fork_user_auth):
                self._cmp_fork_original(fork_user, fork_date, fork.nodes[idx],
                                        child, title_prepend='')

    @mock.patch('framework.status.push_status_message')
    def test_fork_recursion(self, mock_push_status_message):
        """Omnibus test for forking.
        """
        # Make some children
        self.component = NodeFactory(creator=self.user, parent=self.project)
        self.subproject = ProjectFactory(creator=self.user, parent=self.project)

        # Add pointers to test copying
        pointee = ProjectFactory()
        self.project.add_pointer(pointee, auth=self.auth)
        self.component.add_pointer(pointee, auth=self.auth)
        self.subproject.add_pointer(pointee, auth=self.auth)

        # Add add-on to test copying
        self.project.add_addon('github', self.auth)
        self.component.add_addon('github', self.auth)
        self.subproject.add_addon('github', self.auth)

        # Log time
        fork_date = timezone.now()

        # Fork node
        with mock.patch.object(Node, 'bulk_update_search'):
            fork = self.project.fork_node(auth=self.auth)

        # Compare fork to original
        self._cmp_fork_original(self.user, fork_date, fork, self.project)

    def test_fork_private_children(self):
        """Tests that only public components are created

        """
        # Make project public
        self.project.set_privacy('public')
        # Make some children
        self.public_component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Forked',
            is_public=True,
        )
        self.public_subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Forked',
            is_public=True,
        )
        self.private_component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Not Forked',
        )
        self.private_subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Not Forked',
        )
        self.private_subproject_public_component = NodeFactory(
            creator=self.user,
            parent=self.private_subproject,
            title='Not Forked',
        )
        self.public_subproject_public_component = NodeFactory(
            creator=self.user,
            parent=self.private_subproject,
            title='Forked',
        )
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = None
        # New user forks the project
        fork = self.project.fork_node(user2_auth)

        # fork correct children
        assert_equal(len(fork.nodes), 2)
        assert_not_in('Not Forked', [node.title for node in fork.nodes])

    def test_fork_not_public(self):
        self.project.set_privacy('public')
        fork = self.project.fork_node(self.auth)
        assert_false(fork.is_public)

    def test_fork_log_has_correct_log(self):
        fork = self.project.fork_node(self.auth)
        last_log = list(fork.logs)[-1]
        assert_equal(last_log.action, NodeLog.NODE_FORKED)
        # Legacy 'registration' param should be the ID of the fork
        assert_equal(last_log.params['registration'], fork._primary_key)
        # 'node' param is the original node's ID
        assert_equal(last_log.params['node'], self.project._primary_key)

    def test_not_fork_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        fork = self.project.fork_node(self.auth)
        assert_not_in(link, fork.private_links)

    def test_cannot_fork_private_node(self):
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        with assert_raises(PermissionsError):
            self.project.fork_node(user2_auth)

    def test_can_fork_public_node(self):
        self.project.set_privacy('public')
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_true(fork)

    def test_contributor_can_fork(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_true(fork)
        # Forker has admin permissions
        assert_equal(len(fork.contributors), 1)
        assert_equal(fork.get_permissions(user2), ['read', 'write', 'admin'])

    def test_fork_preserves_license(self):
        license = NodeLicenseRecordFactory()
        self.project.node_license = license
        self.project.save()
        fork = self.project.fork_node(self.auth)
        assert_equal(fork.node_license.id, license.id)

    def test_fork_registration(self):
        self.registration = RegistrationFactory(project=self.project)
        fork = self.registration.fork_node(self.auth)

        # fork should not be a registration
        assert_false(fork.is_registration)

        # Compare fork to original
        self._cmp_fork_original(
            self.user,
            timezone.now(),
            fork,
            self.registration,
        )

    def test_fork_project_with_no_wiki_pages(self):
        project = ProjectFactory(creator=self.user)
        fork = project.fork_node(self.auth)
        assert_equal(fork.wiki_pages_versions, {})
        assert_equal(fork.wiki_pages_current, {})
        assert_equal(fork.wiki_private_uuids, {})

    def test_forking_clones_project_wiki_pages(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        wiki = NodeWikiFactory(node=project)
        current_wiki = NodeWikiFactory(node=project, version=2)
        fork = project.fork_node(self.auth)
        assert_equal(fork.wiki_private_uuids, {})

        registration_wiki_current = NodeWikiPage.load(fork.wiki_pages_current[current_wiki.page_name])
        assert_equal(registration_wiki_current.node, fork)
        assert_not_equal(registration_wiki_current._id, current_wiki._id)

        registration_wiki_version = NodeWikiPage.load(fork.wiki_pages_versions[wiki.page_name][0])
        assert_equal(registration_wiki_version.node, fork)
        assert_not_equal(registration_wiki_version._id, wiki._id)


class TestRegisterNode(OsfTestCase):

    def setUp(self):
        super(TestRegisterNode, self).setUp()
        ensure_schemas()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.link = PrivateLinkFactory()
        self.link.nodes.append(self.project)
        self.link.save()
        self.registration = RegistrationFactory(project=self.project)

    def test_factory(self):
        # Create a registration with kwargs
        registration1 = RegistrationFactory(
            title='t1', description='d1', creator=self.user,
        )
        assert_equal(registration1.title, 't1')
        assert_equal(registration1.description, 'd1')
        assert_equal(len(registration1.contributors), 1)
        assert_in(self.user, registration1.contributors)
        assert_equal(registration1.registered_user, self.user)
        assert_equal(len(registration1.private_links), 0)

        # Create a registration from a project
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration2 = RegistrationFactory(
            project=self.project,
            user=user2,
            data={'some': 'data'},
        )
        assert_equal(registration2.registered_from, self.project)
        assert_equal(registration2.registered_user, user2)
        assert_equal(
            registration2.registered_meta[get_default_metaschema()._id],
            {'some': 'data'}
        )

        # Test default user
        assert_equal(self.registration.registered_user, self.user)

    def test_title(self):
        assert_equal(self.registration.title, self.project.title)

    def test_description(self):
        assert_equal(self.registration.description, self.project.description)

    def test_category(self):
        assert_equal(self.registration.category, self.project.category)

    def test_permissions(self):
        assert_false(self.registration.is_public)
        self.project.set_privacy(Node.PUBLIC)
        registration = RegistrationFactory(project=self.project)
        assert_false(registration.is_public)

    def test_contributors(self):
        assert_equal(self.registration.contributors, self.project.contributors)

    def test_forked_from(self):
        # A a node that is not a fork
        assert_equal(self.registration.forked_from, None)
        # A node that is a fork
        fork = self.project.fork_node(self.auth)
        registration = RegistrationFactory(project=fork)
        assert_equal(registration.forked_from, self.project)

    def test_private_links(self):
        assert_not_equal(
            self.registration.private_links,
            self.project.private_links
        )

    def test_creator(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration = RegistrationFactory(project=self.project)
        assert_equal(registration.creator, self.user)

    def test_logs(self):
        # Registered node has all logs except for registration approval initiated
        assert_equal(len(self.project.logs) - 1, len(self.registration.logs))
        assert_equal(len(self.registration.logs), 1)
        assert_equal(self.registration.logs[0].action, 'project_created')
        assert_equal(len(self.project.logs), 2)
        assert_equal(self.project.logs[0].action, 'project_created')
        assert_equal(self.project.logs[1].action, 'registration_initiated')

    def test_tags(self):
        assert_equal(self.registration.tags, self.project.tags)

    def test_nodes(self):

        # Create some nodes
        self.component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Title1',
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Title2',
        )
        self.subproject_component = NodeFactory(
            creator=self.user,
            parent=self.subproject,
            title='Title3',
        )

        # Make a registration
        registration = RegistrationFactory(project=self.project)

        # Reload the registration; else test won't catch failures to save
        registration.reload()

        # Registration has the nodes
        assert_equal(len(registration.nodes), 2)
        assert_equal(
            [node.title for node in registration.nodes],
            [node.title for node in self.project.nodes],
        )
        # Nodes are copies and not the original versions
        for node in registration.nodes:
            assert_not_in(node, self.project.nodes)
            assert_true(node.is_registration)

    def test_private_contributor_registration(self):

        # Create some nodes
        self.component = NodeFactory(
            creator=self.user,
            parent=self.project,
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
        )

        # Create some nodes to share
        self.shared_component = NodeFactory(
            creator=self.user,
            parent=self.project,
        )
        self.shared_subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
        )

        # Share the project and some nodes
        user2 = UserFactory()
        self.project.add_contributor(user2, permissions=(READ, WRITE, ADMIN))
        self.shared_component.add_contributor(user2, permissions=(READ, WRITE, ADMIN))
        self.shared_subproject.add_contributor(user2, permissions=(READ, WRITE, ADMIN))

        # Partial contributor registers the node
        registration = RegistrationFactory(project=self.project, user=user2)

        # The correct subprojects were registered
        assert_equal(len(registration.nodes), len(self.project.nodes))
        for idx in range(len(registration.nodes)):
            assert_true(registration.nodes[idx].is_registration_of(self.project.nodes[idx]))

    def test_is_registration(self):
        assert_true(self.registration.is_registration)

    def test_registered_date(self):
        assert_almost_equal(
            self.registration.registered_date,
            timezone.now(),
            delta=datetime.timedelta(seconds=30),
        )

    def test_registered_addons(self):
        assert_equal(
            [addon.config.short_name for addon in self.registration.get_addons()],
            [addon.config.short_name for addon in self.registration.registered_from.get_addons()],
        )

    def test_registered_user(self):
        # Add a second contributor
        user2 = UserFactory()
        self.project.add_contributor(user2, permissions=(READ, WRITE, ADMIN))
        # Second contributor registers project
        registration = RegistrationFactory(parent=self.project, user=user2)
        assert_equal(registration.registered_user, user2)

    def test_registered_from(self):
        assert_equal(self.registration.registered_from, self.project)

    def test_registered_get_absolute_url(self):
        assert_equal(self.registration.get_absolute_url(),
                     '{}v2/registrations/{}/'
                        .format(settings.API_DOMAIN, self.registration._id)
        )

    def test_registration_list(self):
        assert_in(self.registration._id, [n._id for n in self.project.registrations_all])

    def test_registration_gets_institution_affiliation(self):
        node = NodeFactory()
        institution = InstitutionFactory()
        node.affiliated_institutions.append(institution)
        node.save()
        registration = RegistrationFactory(project=node)
        assert_equal(registration.affiliated_institutions, node.affiliated_institutions)

    def test_registration_of_project_with_no_wiki_pages(self):
        assert_equal(self.registration.wiki_pages_versions, {})
        assert_equal(self.registration.wiki_pages_current, {})
        assert_equal(self.registration.wiki_private_uuids, {})

    @mock.patch('website.project.signals.after_create_registration')
    def test_registration_clones_project_wiki_pages(self, mock_signal):
        project = ProjectFactory(creator=self.user, is_public=True)
        wiki = NodeWikiFactory(node=project)
        current_wiki = NodeWikiFactory(node=project, version=2)
        registration = project.register_node(get_default_metaschema(), Auth(self.user), '', None)
        assert_equal(self.registration.wiki_private_uuids, {})

        registration_wiki_current = NodeWikiPage.load(registration.wiki_pages_current[current_wiki.page_name])
        assert_equal(registration_wiki_current.node, registration)
        assert_not_equal(registration_wiki_current._id, current_wiki._id)

        registration_wiki_version = NodeWikiPage.load(registration.wiki_pages_versions[wiki.page_name][0])
        assert_equal(registration_wiki_version.node, registration)
        assert_not_equal(registration_wiki_version._id, wiki._id)

    def test_legacy_private_registrations_can_be_made_public(self):
        self.registration.is_public = False
        self.registration.set_privacy(Node.PUBLIC, auth=Auth(self.registration.creator))
        assert_true(self.registration.is_public)


class TestNodeLog(OsfTestCase):

    def setUp(self):
        super(TestNodeLog, self).setUp()
        self.log = NodeLogFactory()

    def test_repr(self):
        rep = repr(self.log)
        assert_in(self.log.action, rep)
        assert_in(self.log._id, rep)

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)

    def test_render_log_contributor_unregistered(self):
        node = NodeFactory()
        name, email = fake.name(), fake.email()
        unreg = node.add_unregistered_contributor(fullname=name, email=email,
            auth=Auth(node.creator))
        node.save()

        log = NodeLogFactory(params={'node': node._primary_key})
        ret = log._render_log_contributor(unreg._primary_key)

        assert_false(ret['registered'])
        record = unreg.get_unclaimed_record(node._primary_key)
        assert_equal(ret['fullname'], record['name'])

    def test_render_log_contributor_none(self):
        log = NodeLogFactory()
        assert_equal(log._render_log_contributor(None), None)

    def test_tz_date(self):
        assert_equal(self.log.tz_date.tzinfo, pytz.UTC)

    def test_formatted_date(self):
        iso_formatted = self.log.formatted_date  # The string version in iso format
        # Reparse the date
        parsed = parser.parse(iso_formatted)
        unparsed = self.log.tz_date
        assert_equal(parsed, unparsed)

    def test_can_view(self):
        project = ProjectFactory(is_public=False)

        non_contrib = UserFactory()

        created_log = project.logs[0]
        assert_false(created_log.can_view(project, Auth(user=non_contrib)))
        assert_true(created_log.can_view(project, Auth(user=project.creator)))

    def test_can_view_with_non_related_project_arg(self):
        project = ProjectFactory()
        unrelated = ProjectFactory()

        created_log = project.logs[0]
        assert_false(created_log.can_view(unrelated, Auth(user=project.creator)))

    def test_original_node_and_current_node_for_registration_logs(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        registration = RegistrationFactory(project=project)

        log_project_created_original = project.logs[0]
        log_registration_initiated = project.logs[1]
        log_project_created_registration = registration.logs[0]

        assert_equal(project._id, log_project_created_original.original_node._id)
        assert_equal(project._id, log_project_created_original.node._id)
        assert_equal(project._id, log_registration_initiated.original_node._id)
        assert_equal(project._id, log_registration_initiated.node._id)
        assert_equal(project._id, log_project_created_registration.original_node._id)
        assert_equal(registration._id, log_project_created_registration.node._id)

    def test_original_node_and_current_node_for_fork_logs(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        fork = project.fork_node(auth=Auth(user))

        log_project_created_original = project.logs[0]
        log_project_created_fork = fork.logs[0]
        log_node_forked = fork.logs[1]

        assert_equal(project._id, log_project_created_original.original_node._id)
        assert_equal(project._id, log_project_created_original.node._id)
        assert_equal(project._id, log_project_created_fork.original_node._id)
        assert_equal(fork._id, log_project_created_fork.node._id)
        assert_equal(project._id, log_node_forked.original_node._id)
        assert_equal(fork._id, log_node_forked.node._id)


class TestPermissions(OsfTestCase):

    def setUp(self):
        super(TestPermissions, self).setUp()
        self.project = ProjectFactory()

    def test_default_creator_permissions(self):
        assert_equal(
            set(CREATOR_PERMISSIONS),
            set(self.project.permissions[self.project.creator._id])
        )

    def test_default_contributor_permissions(self):
        user = UserFactory()
        self.project.add_contributor(user, permissions=['read'], auth=Auth(user=self.project.creator))
        self.project.save()
        assert_equal(
            set(['read']),
            set(self.project.get_permissions(user))
        )

    def test_adjust_permissions(self):
        self.project.permissions[42] = ['dance']
        self.project.save()
        assert_not_in(42, self.project.permissions)

    def test_add_permission(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_in(self.project.creator._id, self.project.permissions)
        assert_in('dance', self.project.permissions[self.project.creator._id])

    def test_add_permission_already_granted(self):
        self.project.add_permission(self.project.creator, 'dance')
        with assert_raises(ValueError):
            self.project.add_permission(self.project.creator, 'dance')

    def test_remove_permission(self):
        self.project.add_permission(self.project.creator, 'dance')
        self.project.remove_permission(self.project.creator, 'dance')
        assert_not_in('dance', self.project.permissions[self.project.creator._id])

    def test_remove_permission_not_granted(self):
        with assert_raises(ValueError):
            self.project.remove_permission(self.project.creator, 'dance')

    def test_has_permission_true(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_true(self.project.has_permission(self.project.creator, 'dance'))

    def test_has_permission_false(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_false(self.project.has_permission(self.project.creator, 'sing'))

    def test_has_permission_not_in_dict(self):
        assert_false(self.project.has_permission(self.project.creator, 'dance'))


class TestPointer(OsfTestCase):

    def setUp(self):
        super(TestPointer, self).setUp()
        self.pointer = PointerFactory()

    def test_title(self):
        assert_equal(
            self.pointer.title,
            self.pointer.node.title
        )

    def test_contributors(self):
        assert_equal(
            self.pointer.contributors,
            self.pointer.node.contributors
        )

    def _assert_clone(self, pointer, cloned):
        assert_not_equal(
            pointer._id,
            cloned._id
        )
        assert_equal(
            pointer.node,
            cloned.node
        )

    def test_get_pointer_parent(self):
        parent = ProjectFactory()
        pointed = ProjectFactory()
        parent.add_pointer(pointed, Auth(parent.creator))
        parent.save()
        assert_equal(get_pointer_parent(parent.nodes[0]), parent)

    def test_clone(self):
        cloned = self.pointer._clone()
        self._assert_clone(self.pointer, cloned)

    def test_clone_no_node(self):
        pointer = Pointer()
        cloned = pointer._clone()
        assert_equal(cloned, None)

    def test_fork(self):
        forked = self.pointer.fork_node()
        self._assert_clone(self.pointer, forked)

    def test_register(self):
        registered = self.pointer.fork_node()
        self._assert_clone(self.pointer, registered)

    def test_register_with_pointer_to_registration(self):
        pointee = RegistrationFactory()
        project = ProjectFactory()
        auth = Auth(user=project.creator)
        project.add_pointer(pointee, auth=auth)
        with mock_archive(project) as registration:
            assert_equal(registration.nodes[0].node, pointee)

    def test_has_pointers_recursive_false(self):
        project = ProjectFactory()
        node = NodeFactory(project=project)
        assert_false(project.has_pointers_recursive)
        assert_false(node.has_pointers_recursive)

    def test_has_pointers_recursive_true(self):
        project = ProjectFactory()
        node = NodeFactory(parent=project)
        node.nodes.append(self.pointer)
        assert_true(node.has_pointers_recursive)
        assert_true(project.has_pointers_recursive)


class TestUnregisteredUser(OsfTestCase):

    def setUp(self):
        super(TestUnregisteredUser, self).setUp()
        self.referrer = UserFactory()
        self.project = ProjectFactory(creator=self.referrer)
        self.user = UnregUserFactory()

    def add_unclaimed_record(self):
        given_name = 'Fredd Merkury'
        email = fake.email()
        self.user.add_unclaimed_record(node=self.project,
            given_name=given_name, referrer=self.referrer,
            email=email)
        self.user.save()
        data = self.user.unclaimed_records[self.project._primary_key]
        return email, data

    def test_unregistered_factory(self):
        u1 = UnregUserFactory()
        assert_false(u1.is_registered)
        assert_true(u1.password is None)
        assert_true(u1.fullname)

    def test_unconfirmed_factory(self):
        u = UnconfirmedUserFactory()
        assert_false(u.is_registered)
        assert_true(u.username)
        assert_true(u.fullname)
        assert_true(u.password)
        assert_equal(len(u.email_verifications.keys()), 1)

    def test_add_unclaimed_record(self):
        email, data = self.add_unclaimed_record()
        assert_equal(data['name'], 'Fredd Merkury')
        assert_equal(data['referrer_id'], self.referrer._primary_key)
        assert_in('token', data)
        assert_equal(data['email'], email)
        assert_equal(data, self.user.get_unclaimed_record(self.project._primary_key))

    def test_get_claim_url(self):
        self.add_unclaimed_record()
        uid = self.user._primary_key
        pid = self.project._primary_key
        token = self.user.get_unclaimed_record(pid)['token']
        domain = settings.DOMAIN
        assert_equal(self.user.get_claim_url(pid, external=True),
            '{domain}user/{uid}/{pid}/claim/?token={token}'.format(**locals()))

    def test_get_claim_url_raises_value_error_if_not_valid_pid(self):
        with assert_raises(ValueError):
            self.user.get_claim_url('invalidinput')

    def test_cant_add_unclaimed_record_if_referrer_isnt_contributor(self):
        project = ProjectFactory()  # referrer isn't a contributor to this project
        with assert_raises(PermissionsError):
            self.user.add_unclaimed_record(node=project,
                given_name='fred m', referrer=self.referrer)

    def test_register(self):
        assert_false(self.user.is_registered)  # sanity check
        assert_false(self.user.is_claimed)
        email = fake.email()
        self.user.register(username=email, password='killerqueen')
        self.user.save()
        assert_true(self.user.is_claimed)
        assert_true(self.user.is_registered)
        assert_true(self.user.check_password('killerqueen'))
        assert_equal(self.user.username, email)

    def test_registering_with_a_different_email_adds_to_emails_list(self):
        user = UnregUserFactory()
        assert_equal(user.password, None)  # sanity check
        user.register(username=fake.email(), password='killerqueen')

    def test_verify_claim_token(self):
        self.add_unclaimed_record()
        valid = self.user.get_unclaimed_record(self.project._primary_key)['token']
        assert_true(self.user.verify_claim_token(valid, project_id=self.project._primary_key))
        assert_false(self.user.verify_claim_token('invalidtoken', project_id=self.project._primary_key))

    def test_verify_claim_token_with_no_expiration_date(self):
        # Legacy records may not have an 'expires' key
        self.add_unclaimed_record()
        record = self.user.get_unclaimed_record(self.project._primary_key)
        del record['expires']
        self.user.save()
        token = record['token']
        assert_true(self.user.verify_claim_token(token, project_id=self.project._primary_key))

    def test_claim_contributor(self):
        self.add_unclaimed_record()
        # sanity cheque
        assert_false(self.user.is_registered)
        assert_true(self.project)


class TestTags(OsfTestCase):

    def setUp(self):
        super(TestTags, self).setUp()
        self.project = ProjectFactory()
        self.auth = Auth(self.project.creator)

    def test_add_tag(self):
        self.project.add_tag('scientific', auth=self.auth)
        assert_in('scientific', self.project.tags)
        assert_equal(
            self.project.logs.latest().action,
            NodeLog.TAG_ADDED
        )

    def test_add_tag_too_long(self):
        with assert_raises(ValidationError):
            self.project.add_tag('q' * 129, auth=self.auth)

    def test_remove_tag(self):
        self.project.add_tag('scientific', auth=self.auth)
        self.project.remove_tag('scientific', auth=self.auth)
        assert_not_in('scientific', self.project.tags)
        assert_equal(
            self.project.logs.latest().action,
            NodeLog.TAG_REMOVED
        )

    def test_remove_tag_not_present(self):
        with assert_raises(TagNotFoundError):
            self.project.remove_tag('scientific', auth=self.auth)


class TestContributorVisibility(OsfTestCase):

    def setUp(self):
        super(TestContributorVisibility, self).setUp()
        self.project = ProjectFactory()
        self.user2 = UserFactory()
        self.project.add_contributor(self.user2)

    def test_get_visible_true(self):
        assert_true(self.project.get_visible(self.project.creator))

    def test_get_visible_false(self):
        self.project.set_visible(self.project.creator, False)
        assert_false(self.project.get_visible(self.project.creator))

    def test_make_invisible(self):
        self.project.set_visible(self.project.creator, False, save=True)
        self.project.reload()
        assert_not_in(
            self.project.creator._id,
            self.project.visible_contributor_ids
        )
        assert_not_in(
            self.project.creator,
            self.project.visible_contributors
        )
        assert_equal(
            self.project.logs.latest().action,
            NodeLog.MADE_CONTRIBUTOR_INVISIBLE
        )

    def test_make_visible(self):
        self.project.set_visible(self.project.creator, False, save=True)
        self.project.set_visible(self.project.creator, True, save=True)
        self.project.reload()
        assert_in(
            self.project.creator._id,
            self.project.visible_contributor_ids
        )
        assert_in(
            self.project.creator,
            self.project.visible_contributors
        )
        assert_equal(
            self.project.logs.latest().action,
            NodeLog.MADE_CONTRIBUTOR_VISIBLE
        )
        # Regression test: Ensure that hiding and showing the first contributor
        # does not change the visible contributor order
        assert_equal(
            self.project.visible_contributors,
            [self.project.creator, self.user2]
        )

    def test_set_visible_missing(self):
        with assert_raises(ValueError):
            self.project.set_visible(UserFactory(), True)


class TestProjectWithAddons(OsfTestCase):

    def test_factory(self):
        p = ProjectWithAddonFactory(addon='s3')
        assert_true(p.get_addon('s3'))
        assert_true(p.creator.get_addon('s3'))


class TestPrivateLink(OsfTestCase):

    def test_node_scale(self):
        link = PrivateLinkFactory()
        project = ProjectFactory()
        comp = NodeFactory(parent=project)
        link.nodes.append(project)
        link.save()
        assert_equal(link.node_scale(project), -40)
        assert_equal(link.node_scale(comp), -20)

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_to_json_nodes_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = ProjectFactory(is_deleted=True)
        node = NodeFactory(project=project)
        link.nodes.extend([project, node])
        link.save()
        result = link.to_json()
        # result doesn't include deleted parent
        assert_equal(len(result['nodes']), 1)

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_node_scale_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = ProjectFactory(is_deleted=True)
        node = NodeFactory(project=project)
        link.nodes.extend([project, node])
        link.save()
        assert_equal(link.node_scale(node), -40)

    def test_create_from_node(self):
        ensure_schemas()
        proj = ProjectFactory()
        user = proj.creator
        schema = MetaSchema.find()[0]
        data = {'some': 'data'}
        draft = DraftRegistration.create_from_node(
            proj,
            user=user,
            schema=schema,
            data=data,
        )
        assert_equal(user, draft.initiator)
        assert_equal(schema, draft.registration_schema)
        assert_equal(data, draft.registration_metadata)
        assert_equal(proj, draft.branched_from)


class TestNodeAddContributorRegisteredOrNot(OsfTestCase):

    def setUp(self):
        super(TestNodeAddContributorRegisteredOrNot, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_add_contributor_user_id(self):
        self.registered_user = UserFactory()
        contributor = self.node.add_contributor_registered_or_not(auth=Auth(self.user), user_id=self.registered_user._id, save=True)
        assert_in(contributor._id, self.node.contributors)
        assert_equals(contributor.is_registered, True)

    def test_add_contributor_user_id_already_contributor(self):
        with assert_raises(ValidationValueError) as e:
            self.node.add_contributor_registered_or_not(auth=Auth(self.user), user_id=self.user._id, save=True)
        assert_in('is already a contributor', e.exception.message)

    def test_add_contributor_invalid_user_id(self):
        with assert_raises(ValueError) as e:
            self.node.add_contributor_registered_or_not(auth=Auth(self.user), user_id='abcde', save=True)
        assert_in('was not found', e.exception.message)

    def test_add_contributor_fullname_email(self):
        contributor = self.node.add_contributor_registered_or_not(auth=Auth(self.user), full_name='Jane Doe', email='jane@doe.com')
        assert_in(contributor._id, self.node.contributors)
        assert_equals(contributor.is_registered, False)

    def test_add_contributor_fullname(self):
        contributor = self.node.add_contributor_registered_or_not(auth=Auth(self.user), full_name='Jane Doe')
        assert_in(contributor._id, self.node.contributors)
        assert_equals(contributor.is_registered, False)

    def test_add_contributor_fullname_email_already_exists(self):
        self.registered_user = UserFactory()
        contributor = self.node.add_contributor_registered_or_not(auth=Auth(self.user), full_name='F Mercury', email=self.registered_user.username)
        assert_in(contributor._id, self.node.contributors)
        assert_equals(contributor.is_registered, True)


class TestNodeSpam(OsfTestCase):

    def setUp(self):
        super(TestNodeSpam, self).setUp()
        self.node = ProjectFactory(is_public=True)

    def test_flag_spam_make_node_private(self):
        assert_true(self.node.is_public)
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', True):
            self.node.flag_spam()
        assert_true(self.node.is_spammy)
        assert_false(self.node.is_public)

    def test_flag_spam_do_not_make_node_private(self):
        assert_true(self.node.is_public)
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', False):
            self.node.flag_spam()
        assert_true(self.node.is_spammy)
        assert_true(self.node.is_public)

    def test_confirm_spam_makes_node_private(self):
        assert_true(self.node.is_public)
        self.node.confirm_spam()
        assert_true(self.node.is_spammy)
        assert_false(self.node.is_public)


class TestOnNodeUpdate(OsfTestCase):

    def setUp(self):
        super(TestOnNodeUpdate, self).setUp()
        self.user = UserFactory()
        self.session = SessionFactory(user=self.user)
        set_session(self.session)
        self.node = ProjectFactory(is_public=True)

    def tearDown(self):
        handlers.celery_before_request()
        super(TestOnNodeUpdate, self).tearDown()

    @mock.patch('website.project.model.enqueue_task')
    def test_enqueue_called(self, enqueue_task):
        self.node.title = 'A new title'
        self.node.save()

        (task, ) = enqueue_task.call_args[0]

        assert_equals(task.task, 'website.project.tasks.on_node_updated')
        assert_equals(task.args[0], self.node._id)
        assert_equals(task.args[1], self.user._id)
        assert_equals(task.args[2], False)
        assert_equals(task.args[3], {'title'})

    @mock.patch('website.project.tasks.settings.SHARE_URL', None)
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', None)
    @mock.patch('website.project.tasks.requests')
    def test_skips_no_settings(self, requests):
        on_node_updated(self.node._id, self.user._id, False, {'is_public'})
        assert_false(requests.post.called)

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    def test_updates_share(self, requests):
        on_node_updated(self.node._id, self.user._id, False, {'is_public'})

        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']

        assert_true(requests.post.called)
        assert_equals(kwargs['headers']['Authorization'], 'Bearer Token')
        assert_equals(graph[0]['uri'], '{}{}/'.format(settings.DOMAIN, self.node._id))

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    def test_update_share_correctly(self, requests):
        cases = [{
            'is_deleted': False,
            'attrs': {'is_public': True, 'is_deleted': False, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': False, 'is_deleted': False, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': True, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': False, 'spam_status': SpamStatus.SPAM}
        }]

        for case in cases:
            for attr, value in case['attrs'].items():
                setattr(self.node, attr, value)
            self.node.save()

            on_node_updated(self.node._id, self.user._id, False, {'is_public'})

            kwargs = requests.post.call_args[1]
            graph = kwargs['json']['data']['attributes']['data']['@graph']
            assert_equals(graph[1]['is_deleted'], case['is_deleted'])


if __name__ == '__main__':
    unittest.main()
