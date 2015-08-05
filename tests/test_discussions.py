# -*- coding: utf-8 -*-

import mock

from nose.tools import *  # noqa; PEP8 asserts

from tests.factories import ProjectFactory, NodeFactory, RegistrationFactory, UserFactory, AuthUserFactory
from tests.base import OsfTestCase

from framework.auth.decorators import Auth

from website import mails
from website.util import api_url_for


class TestNewNodeDiscussions(OsfTestCase):

    def test_node_creates_discussions(self):
        node = NodeFactory()
        assert_true(node.discussions)

    def test_node_adds_and_subscribes_creator(self):
        user = UserFactory()
        node = NodeFactory(creator=user)
        assert_in(user.email, node.discussions.emails)
        assert_in(user.email, node.discussions.subscriptions)

    def test_top_level_project_enables_discussions(self):
        project = ProjectFactory(parent=None)
        assert_true(project.discussions.is_enabled)

    def test_project_with_parent_disables_discussions(self):
        parent = ProjectFactory(parent=None)
        child = ProjectFactory(parent=parent)
        assert_false(child.discussions.is_enabled)

    def test_forking_node_creates_discussions(self):
        user = AuthUserFactory()
        node = NodeFactory(is_public=True)
        fork = node.fork_node(Auth(user=user))
        assert_true(fork.discussions)

    def test_forking_node_adds_forker(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        project = ProjectFactory(creator=user1, parent=None, is_public=True)

        fork1 = project.fork_node(Auth(user=user1))
        assert_in(user1.email, fork1.discussions.emails)

        fork2 = project.fork_node(Auth(user=user2))
        assert_in(user2.email, fork2.discussions.emails)
        assert_not_in(user1.email, fork2.discussions.emails)

    def test_forking_with_child_enables_only_parent(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        parent_fork = parent.fork_node(Auth(user=user))
        child_fork = parent_fork.nodes[0]

        assert_true(parent_fork.discussions.is_enabled)
        assert_false(child_fork.discussions.is_enabled)

    def test_using_as_template_creates_discussions(self):
        user = AuthUserFactory()
        node = NodeFactory(is_public=True)
        new = node.use_as_template(Auth(user=user))
        assert_true(new.discussions)

    def test_using_as_template_adds_templater(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        project = ProjectFactory(creator=user1, parent=None, is_public=True)

        new1 = project.use_as_template(Auth(user=user1))
        assert_in(user1.email, new1.discussions.emails)

        new2 = project.use_as_template(Auth(user=user2))
        assert_in(user2.email, new2.discussions.emails)
        assert_not_in(user1.email, new2.discussions.emails)

    def test_template_with_child_enables_only_parent(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        new_parent = parent.use_as_template(Auth(user=user))
        new_child = new_parent.nodes[0]

        assert_true(new_parent.discussions.is_enabled)
        assert_false(new_child.discussions.is_enabled)

    def test_registration_creates_discussions_with_no_setup(self):
        reg = RegistrationFactory()

        assert_true(reg.discussions)
        assert_false(reg.discussions.node_id)


class TestDiscussionsOnProjectActions(OsfTestCase):

    def setUp(self):
        super(TestDiscussionsOnProjectActions, self).setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator, parent=None)
        self.discussions = self.project.discussions

    def test_add_single_contributor_adds_and_subscribes(self):
        user = UserFactory()

        self.project.add_contributor(user, save=True)

        assert_equal(self.discussions.emails, {user.email, self.creator.email})
        assert_equal(self.discussions.subscriptions, {user.email, self.creator.email})

    def test_add_many_contributors_adds_and_subscribes_all(self):
        users = [UserFactory() for i in range(10)]
        emails = {user.email for user in users + [self.creator]}

        for user in users:
            self.project.add_contributor(user, save=False)
        self.project.save()

        assert_equal(self.discussions.emails, emails)
        assert_equal(self.discussions.subscriptions, emails)

    def test_add_contributor_then_remove_creator(self):
        user = UserFactory()

        self.project.add_contributor(user, permissions=('read', 'write', 'admin'), save=True)
        self.project.remove_contributor(self.creator, auth=Auth(user=self.creator), save=True)

        assert_equal(self.discussions.emails, {user.email})
        assert_equal(self.discussions.subscriptions, {user.email})

    def test_add_contributors_then_remove_some(self):
        users = {UserFactory() for i in range(10)}

        for user in users:
            self.project.add_contributor(user, save=False)
        self.project.save()

        for i in range(5):
            user = users.pop()
            self.project.remove_contributor(user, auth=Auth(self.creator))
        self.project.save()

        users = list(users)
        emails = {user.email for user in users + [self.creator]}

        assert_equal(self.discussions.emails, emails)
        assert_equal(self.discussions.subscriptions, emails)

    def test_delete_project_disables_discussions(self):
        assert_true(self.discussions.is_enabled)

        self.project.remove_node(Auth(user=self.creator))

        assert_false(self.discussions.is_enabled)
        assert_true(self.discussions.node_deleted)


class TestEmailRejections(OsfTestCase):

    def setUp(self):
        super(TestEmailRejections, self).setUp()
        self.user = AuthUserFactory()
        self.user.reload()
        self.project = ProjectFactory(creator=self.user, parent=None)
        # TODO this email will need to be updated when we start logging, since an actual message,
        # and potentially other dictionary items, will become necessary
        self.message = {
            'To': '{}@osf.io'.format(self.project._id),
            'From': self.user.email,
            'subject': 'Hi, Friend!',
            'stripped-text': 'Are you really my friend?'
        }
        self.post_url = api_url_for('route_message')

    @mock.patch('website.mails.send_mail')
    def test_working_email(self, mock_send_mail):
        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_not_called()

    @mock.patch('website.mails.send_mail')
    def test_email_from_non_registered_user(self, mock_send_mail):
        self.message['From'] = 'non-email@osf.fake'

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='no_user',
            to_addr='non-email@osf.fake',
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=None,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False
        )

    @mock.patch('website.mails.send_mail')
    def test_email_to_nonexistent_project(self, mock_send_mail):
        self.message['To'] = 'notarealprojectid@osf.io'

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='node_dne',
            to_addr=self.user.email,
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='notarealprojectid@osf.io',
            user=self.user,
            node_type='',
            node_url='',
            is_admin=False
        )

    @mock.patch('website.mails.send_mail')
    def test_email_to_deleted_project(self, mock_send_mail):
        self.project.remove_node(auth=Auth(user=self.user))

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='node_deleted',
            to_addr=self.user.email,
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=True
        )

    @mock.patch('website.mails.send_mail')
    def test_email_to_private_project_without_access(self, mock_send_mail):
        self.user = UserFactory()
        self.user.reload()
        self.message['From'] = self.user.email

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='private_no_access',
            to_addr=self.user.email,
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False
        )

    @mock.patch('website.mails.send_mail')
    def test_email_to_public_project_without_access(self, mock_send_mail):
        self.project.is_public = True
        self.project.save()
        self.user = UserFactory()
        self.user.reload()
        self.message['From'] = self.user.email

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='no_access',
            to_addr=self.user.email,
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False
        )

    @mock.patch('website.mails.send_mail')
    def test_email_to_project_with_discussions_disabled_as_admin(self, mock_send_mail):
        self.project.discussions.disable(save=True)

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='discussions_disabled',
            to_addr=self.user.email,
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=True
        )

    @mock.patch('website.mails.send_mail')
    def test_email_to_project_with_discussions_disabled_as_non_admin(self, mock_send_mail):
        self.user = UserFactory()
        self.user.reload()
        self.project.add_contributor(self.user, save=True)
        self.project.discussions.disable(save=True)
        self.message['From'] = self.user.email

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='discussions_disabled',
            to_addr=self.user.email,
            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False
        )
