# -*- coding: utf-8 -*-

import mock

from nose.tools import *  # noqa; PEP8 asserts

from tests.factories import (
    ProjectFactory, NodeFactory, RegistrationFactory,
    UserFactory, AuthUserFactory, CollectionFactory,
)
from tests.base import OsfTestCase

from framework.auth.decorators import Auth
from framework.auth.signals import user_confirmed
from werkzeug.datastructures import ImmutableMultiDict

from website import mails, settings
from website.mailing_list.utils import get_unsubscribes
from website.mailing_list.model import MailingListEventLog
from website.util import api_url_for


# TODO: prevent or mock queued tasks

class TestNodeCreationMailingConfig(OsfTestCase):

    def test_top_level_project_enables_mailing_list(self):
        project = ProjectFactory(parent=None)
        assert_true(project.mailing_enabled)

    def test_project_with_parent_enables_mailing_list(self):
        parent = ProjectFactory(parent=None)
        child = ProjectFactory(parent=parent)
        assert_true(child.mailing_enabled)

    def test_forking_with_child_enables_mailing_list(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        parent_fork = parent.fork_node(Auth(user=user))
        child_fork = parent_fork.nodes[0]

        assert_true(parent_fork.mailing_enabled)
        assert_true(child_fork.mailing_enabled)

    def test_template_with_child_enables_mailing_list(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        new_parent = parent.use_as_template(Auth(user=user))
        new_child = new_parent.nodes[0]

        assert_true(new_parent.mailing_enabled)
        assert_true(new_child.mailing_enabled)

    def test_registration_disables_mailing_list(self):
        reg = RegistrationFactory()
        assert_false(reg.mailing_enabled)

    def test_collection_disables_mailing_list(self):
        coll = CollectionFactory()
        assert_false(coll.mailing_enabled)


class TestMailingListViews(OsfTestCase):

    def setUp(self):
        super(TestMailingListViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, parent=None)

    def test_unclaimed_user_behavior(self):
        unreg = self.project.add_unregistered_contributor('Billy', 'billy@gmail.com', Auth(self.user))
        self.project.reload()

        assert_in(unreg, get_unsubscribes(self.project))

        unreg.register(username='billy@gmail.com', password='password1')
        assert(unreg.is_registered)

        self.project.reload()
        assert_not_in(unreg, get_unsubscribes(self.project))


    def test_disable_and_enable_project_mailing_list(self):
        url = api_url_for('enable_mailing_list', pid=self.project._id)
        payload = {}

        assert_true(self.project.mailing_enabled)

        self.app.delete(url, payload, auth=self.user.auth)
        self.project.reload()
        assert_false(self.project.mailing_enabled)

        self.app.post(url, payload, auth=self.user.auth)
        self.project.reload()
        assert_true(self.project.mailing_enabled)
