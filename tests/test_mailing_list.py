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
            'stripped-text': 'Are you really my friend?',
            'Content-Type': 'multipart/fake',
        }
        self.post_url = api_url_for('route_message')

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_working_email(self, mock_send_list, mock_send_mail):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2, save=True)
        self.app.post(self.post_url, self.message)

        assert mock_send_mail.call_count == 0
        # Due to unicode/str non-equality in assert_called_with:
        assert_equal(mock_send_list.call_count, 1)
        assert_equal(mock_send_list.call_args[0][0]._id, self.project._id)
        assert_equal(mock_send_list.call_args[0][1]._id, self.user._id)
        assert_equal(len(mock_send_list.call_args[0][2]), 1)
        assert_equal(mock_send_list.call_args[0][2][0]._id, user2._id)
        [assert_equal(mock_send_list.call_args[0][3][key], self.message[key])
            for key in self.message.keys()]

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_no_recipients(self, mock_send_list, mock_send_mail):
        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='no_recipients',
            to_addr=self.user.email,
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=True,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

            
    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_bounce(self, mock_send_list, mock_send_mail):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2, save=True)
        self.message['Content-Type'] = 'multipart/report report-type/delivery-status'
        self.app.post(self.post_url, self.message)

        assert mock_send_mail.call_count == 0
        assert mock_send_list.call_count == 0    

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_auto_reply(self, mock_send_list, mock_send_mail):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2, save=True)
        self.message['subject'] = 'Auto Reply from {}'.format(self.user.fullname)
        self.app.post(self.post_url, self.message)

        assert mock_send_mail.call_count == 0
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_email_from_non_registered_user(self, mock_send_list, mock_send_mail):
        self.message['From'] = 'non-email@osf.fake'

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='no_user',
            to_addr='non-email@osf.fake',
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=None,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_email_to_nonexistent_project(self, mock_send_list, mock_send_mail):
        self.message['To'] = 'notarealprojectid@osf.io'

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='node_dne',
            to_addr=self.user.email,
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='notarealprojectid@osf.io',
            user=self.user,
            node_type='',
            node_url='',
            is_admin=False,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_email_to_deleted_project(self, mock_send_list, mock_send_mail):
        self.project.remove_node(auth=Auth(user=self.user))

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='node_deleted',
            to_addr=self.user.email,
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=True,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_email_to_private_project_without_access(self, mock_send_list, mock_send_mail):
        self.user = UserFactory()
        self.user.reload()
        self.message['From'] = self.user.email

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='no_access',
            to_addr=self.user.email,
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
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
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_email_to_project_with_mailing_list_disabled_as_admin(self, mock_send_list, mock_send_mail):
        self.project.mailing_enabled = False
        self.project.save()

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='mailing_list_disabled',
            to_addr=self.user.email,
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=True,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.mailing_list.utils.send_acception')
    def test_email_to_project_with_mailing_list_disabled_as_non_admin(self, mock_send_list, mock_send_mail):
        self.user = UserFactory()
        self.user.reload()
        self.project.mailing_enabled = False
        self.project.add_contributor(self.user, save=True)
        self.message['From'] = self.user.email

        self.app.post(self.post_url, self.message)

        mock_send_mail.assert_called_with(
            reason='mailing_list_disabled',
            to_addr=self.user.email,
            mail=mails.MAILING_LIST_EMAIL_REJECTED,
            target_address='{}@osf.io'.format(self.project._id),
            user=self.user,
            node_type='project',
            node_url=self.project.absolute_url,
            is_admin=False,
            mail_log_class=MailingListEventLog
        )
        assert mock_send_list.call_count == 0
