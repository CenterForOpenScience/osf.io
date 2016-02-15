# -*- coding: utf-8 -*-

import mock

from nose.tools import *  # noqa; PEP8 asserts

from tests.factories import (
    ProjectFactory, NodeFactory, RegistrationFactory,
    UserFactory, AuthUserFactory, DashboardFactory,
)
from tests.base import OsfTestCase

from framework.auth.decorators import Auth
from framework.auth.signals import user_confirmed

from website import mails, settings
from website.util import api_url_for


class TestNewNodeMailingEnabled(OsfTestCase):

    def test_top_level_project_enables_discussions(self):
        project = ProjectFactory(parent=None)
        assert_true(project.mailing_enabled)

    def test_project_with_parent_enables_discussions(self):
        parent = ProjectFactory(parent=None)
        child = ProjectFactory(parent=parent)
        assert_true(child.mailing_enabled)

    def test_forking_with_child_enables_discussion(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        parent_fork = parent.fork_node(Auth(user=user))
        child_fork = parent_fork.nodes[0]

        assert_true(parent_fork.mailing_enabled)
        assert_true(child_fork.mailing_enabled)

    def test_template_with_child_enables_discussion(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        new_parent = parent.use_as_template(Auth(user=user))
        new_child = new_parent.nodes[0]

        assert_true(new_parent.mailing_enabled)
        assert_true(new_child.mailing_enabled)

    def test_registration_disables_discussions(self):
        reg = RegistrationFactory()
        assert_false(reg.mailing_enabled)

    def test_dashboard_disables_discussions(self):
        dash = DashboardFactory()
        assert_false(dash.mailing_enabled)


class TestDiscussionsOnUserActions(OsfTestCase):

    def setUp(self):
        super(TestDiscussionsOnUserActions, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, parent=None)

    def test_unclaimed_user_behavior(self):
        unreg = self.project.add_unregistered_contributor('Billy', 'billy@gmail.com', Auth(self.user))
        self.project.reload()

        assert_in(unreg, self.project.mailing_unsubs)

        unreg.register(username='billy@gmail.com', password='password1')
        assert(unreg.is_registered)

        self.project.reload()
        assert_not_in(unreg, self.project.mailing_unsubs)


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
    @mock.patch('website.project.mailing_list.send_messages')
    def test_working_email(self, mock_send_list, mock_send_mail):
        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_not_called()
        mock_send_list.assert_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_from_non_registered_user(self, mock_send_list, mock_send_mail):
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
        mock_send_list.assert_not_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_to_nonexistent_project(self, mock_send_list, mock_send_mail):
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
        mock_send_list.assert_not_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_to_deleted_project(self, mock_send_list, mock_send_mail):
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
        mock_send_list.assert_not_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_to_private_project_without_access(self, mock_send_list, mock_send_mail):
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
        mock_send_list.assert_not_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_to_public_project_without_access(self, mock_send_list, mock_send_mail):
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
        mock_send_list.assert_not_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_to_project_with_discussions_disabled_as_admin(self, mock_send_list, mock_send_mail):
        self.project.mailing_enabled = False
        self.project.save()

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
        mock_send_list.assert_not_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.mailing_list.send_messages')
    def test_email_to_project_with_discussions_disabled_as_non_admin(self, mock_send_list, mock_send_mail):
        self.user = UserFactory()
        self.user.reload()
        self.project.mailing_enabled = False
        self.project.add_contributor(self.user, save=True)
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
        mock_send_list.assert_not_called()
