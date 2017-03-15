# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest

import mock
from framework.auth import Auth
from framework.celery_tasks import handlers
from framework.sessions import set_session
#from modularodm.exceptions import ValidationError, ValidationValueError
from osf.exceptions import ValidationValueError
from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase
from tests.factories import (AuthUserFactory, NodeFactory,
                             PointerFactory, ProjectFactory,
                             RegistrationFactory,
                             SessionFactory, UserFactory)
from tests.utils import mock_archive
from website import settings
from website.project.model import Pointer, get_pointer_parent
from website.project.spam.model import SpamStatus
from website.project.tasks import on_node_updated

GUID_FACTORIES = UserFactory, NodeFactory, ProjectFactory


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
