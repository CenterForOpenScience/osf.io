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
from werkzeug.datastructures import ImmutableMultiDict

from website import mails, settings
from website.util import api_url_for


class TestNodeCreationMailingConfig(OsfTestCase):

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


class TestDiscussionsViews(OsfTestCase):

    def setUp(self):
        super(TestDiscussionsViews, self).setUp()
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


    def test_disable_and_enable_project_discussions(self):
        url = api_url_for('enable_discussions', pid=self.project._id)
        payload = {}

        assert_true(self.project.mailing_enabled)

        self.app.delete(url, payload, auth=self.user.auth)
        self.project.reload()
        assert_false(self.project.mailing_enabled)

        self.app.post(url, payload, auth=self.user.auth)
        self.project.reload()
        assert_true(self.project.mailing_enabled)

    def test_set_subscription_false_then_true(self):
        url = api_url_for('set_subscription', pid=self.project._id)

        assert_not_in(self.user, self.project.mailing_unsubs)

        payload = {'discussionsSub': 'unsubscribed'}
        self.app.post_json(url, payload, auth=self.user.auth)
        self.project.reload()
        assert_in(self.user, self.project.mailing_unsubs)

        payload = {'discussionsSub': 'subscribed'}
        self.app.post_json(url, payload, auth=self.user.auth)
        self.project.reload()
        assert_not_in(self.user, self.project.mailing_unsubs)

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
    @mock.patch('website.project.views.discussions.send_messages')
    def test_working_email(self, mock_send_list, mock_send_mail):
        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_not_called()
        # Due to unicode/str non-equality in assert_called_with:
        assert_equal(mock_send_list.call_count, 1)
        assert_equal(mock_send_list.call_args[0][0]._id, self.project._id)
        assert_equal(mock_send_list.call_args[0][1]._id, self.user._id)
        [assert_equal(mock_send_list.call_args[0][2][key], self.message[key])
            for key in self.message.keys()]

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.project.views.discussions.send_messages')
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
    @mock.patch('website.project.views.discussions.send_messages')
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
    @mock.patch('website.project.views.discussions.send_messages')
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
    @mock.patch('website.project.views.discussions.send_messages')
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
    @mock.patch('website.project.views.discussions.send_messages')
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
    @mock.patch('website.project.views.discussions.send_messages')
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
    @mock.patch('website.project.views.discussions.send_messages')
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
