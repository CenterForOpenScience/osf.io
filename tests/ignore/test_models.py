# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest

import mock
from framework.auth import Auth
from framework.celery_tasks import handlers
from framework.exceptions import PermissionsError
from framework.sessions import set_session
#from modularodm.exceptions import ValidationError, ValidationValueError
from osf.exceptions import ValidationError, ValidationValueError
from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase, fake
from tests.factories import (AuthUserFactory, NodeFactory,
                             PointerFactory,
                             PrivateLinkFactory, ProjectFactory,
                             ProjectWithAddonFactory, RegistrationFactory,
                             SessionFactory, UnconfirmedUserFactory,
                             UnregUserFactory, UserFactory)
from tests.utils import mock_archive
from website import settings
from website.exceptions import TagNotFoundError
from website.project.model import (DraftRegistration, MetaSchema, Node,
                                   NodeLog, Pointer, ensure_schemas,
                                   get_pointer_parent)
from website.project.spam.model import SpamStatus
from website.project.tasks import on_node_updated
from website.util.permissions import CREATOR_PERMISSIONS

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
