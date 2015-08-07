# -*- coding: utf-8 -*-

import mock

from nose.tools import *  # noqa; PEP8 asserts

from tests.factories import ProjectFactory, NodeFactory, RegistrationFactory, UserFactory, AuthUserFactory
from tests.base import OsfTestCase

from framework.auth.decorators import Auth

from website import mails, settings
from website.util import api_url_for


class TestNewNodeMailingEnabled(OsfTestCase):

    @mock.patch('website.project.model.mailing_list.create_list')
    def test_node_with_mailing_enabled_creates_discussions(self, mock_create_list):
        node = NodeFactory(mailing_enabled=True)
        mock_create_list.assert_called()

    def test_top_level_project_enables_discussions(self):
        project = ProjectFactory(parent=None)
        assert_true(project.mailing_enabled)

    def test_project_with_parent_disables_discussions(self):
        parent = ProjectFactory(parent=None)
        child = ProjectFactory(parent=parent)
        assert_false(child.mailing_enabled)

    def test_forking_with_child_enables_only_parent(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        parent_fork = parent.fork_node(Auth(user=user))
        child_fork = parent_fork.nodes[0]

        assert_true(parent_fork.mailing_enabled)
        assert_false(child_fork.mailing_enabled)

    def test_template_with_child_enables_only_parent(self):
        user = AuthUserFactory()
        parent = ProjectFactory(parent=None, is_public=True)
        child = NodeFactory(parent=parent, is_public=True)

        new_parent = parent.use_as_template(Auth(user=user))
        new_child = new_parent.nodes[0]

        assert_true(new_parent.mailing_enabled)
        assert_false(new_child.mailing_enabled)

    def test_registration_creates_discussions_with_no_setup(self):
        reg = RegistrationFactory()
        assert_false(reg.mailing_enabled)


class TestListCreation(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestListCreation, cls).setUpClass()
        settings.ENABLE_PROJECT_MAILING = True

    @mock.patch('website.project.model.mailing_list.create_list')
    def test_node_with_mailing_enabled_creates_discussions(self, mock_create_list):
        node = NodeFactory(mailing_enabled=True)
        mock_create_list.assert_called()

    @mock.patch('website.project.model.mailing_list.create_list')
    def test_forking_node_creates_unique_discussions(self, mock_create_list):
        user = AuthUserFactory()
        node = NodeFactory(is_public=True)
        fork = node.fork_node(Auth(user=user))
        mock_create_list.assert_called_with(title=fork.title, **fork.mailing_params)

    @mock.patch('website.project.model.mailing_list.create_list')
    def test_using_as_template_creates_unique_discussions(self, mock_create_list):
        user = AuthUserFactory()
        node = NodeFactory(is_public=True)
        new = node.use_as_template(Auth(user=user))
        mock_create_list.assert_called_with(title=new.title, **new.mailing_params)


class TestNodeMailingParams(OsfTestCase):

    def setUp(self):
        super(TestNodeMailingParams, self).setUp()
        self.creator = UserFactory()
        self.user = UserFactory()

        self.project = ProjectFactory(creator=self.creator, parent=None, is_public=True)
        self.project.add_contributor(self.user)
        self.project.mailing_unsubs.append(self.user)
        self.project.save()
        self.project.reload()

        self.intended_params = {
            'node_id': self.project._id,
            'url': self.project.absolute_url,
            'contributors': [self.creator.email, self.user.email],
            'unsubs': [self.user.email]
        }

    def test_base_mailing_params(self):
        assert_equal(self.project.mailing_params, self.intended_params)

    def test_add_and_unsub_users(self):
        url = api_url_for('set_subscription', pid=self.project._id)
        users = [AuthUserFactory() for i in range(10)]

        for user in users:
            self.project.add_contributor(user)
        self.project.save()
        self.project.reload()

        self.intended_params['contributors'].extend([user.email for user in users])
        assert_equal(self.project.mailing_params, self.intended_params)

        for user in users:
            self.app.post_json(url, {'discussionsSub': 'unsubscribed'}, auth=user.auth)
        self.project.reload()

        self.intended_params['unsubs'].extend(user.email for user in users)
        assert_equal(self.project.mailing_params, self.intended_params)

    def test_fork_has_unique_params(self):
        user = AuthUserFactory()
        fork = self.project.fork_node(Auth(user=user))

        assert_equal(fork.mailing_params, {
            'node_id': fork._id,
            'url': fork.absolute_url,
            'contributors': [user.email],
            'unsubs': []
        })

    def test_templated_has_unique_params(self):
        user = AuthUserFactory()
        new = self.project.use_as_template(Auth(user=user))

        assert_equal(new.mailing_params, {
            'node_id': new._id,
            'url': new.absolute_url,
            'contributors': [user.email],
            'unsubs': []
        })


class TestDiscussionsOnProjectActions(OsfTestCase):

    def setUp(self):
        super(TestDiscussionsOnProjectActions, self).setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator, parent=None)

    @mock.patch('website.project.model.mailing_list.match_members')
    def test_add_single_contributor_updates(self, mock_match_members):
        user = UserFactory()

        self.project.add_contributor(user, save=True)

        mock_match_members.assert_called_with(**self.project.mailing_params)

    @mock.patch('website.project.model.mailing_list.match_members')
    def test_add_many_contributors_updates_only_once(self, mock_match_members):
        users = [UserFactory() for i in range(10)]
        emails = {user.email for user in users + [self.creator]}

        for user in users:
            self.project.add_contributor(user, save=False)
        self.project.save()

        mock_match_members.assert_called_once_with(**self.project.mailing_params)

    @mock.patch('website.project.model.mailing_list.match_members')
    def test_add_contributor_then_remove_creator(self, mock_match_members):
        user = UserFactory()

        self.project.add_contributor(user, permissions=('read', 'write', 'admin'), save=True)
        mock_match_members.assert_called_with(**self.project.mailing_params)

        self.project.remove_contributor(self.creator, auth=Auth(user=self.creator), save=True)
        self.project.reload()
        mock_match_members.assert_called_with(**self.project.mailing_params)

    @mock.patch('website.project.model.mailing_list.delete_list')
    def test_delete_project_disables_discussions(self, mock_delete_list):
        assert_true(self.project.mailing_enabled)

        self.project.remove_node(Auth(user=self.creator))

        assert_false(self.project.mailing_enabled)
        mock_delete_list.assert_called()


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

    @mock.patch('website.mails.send_mail')
    def test_email_to_project_with_discussions_disabled_as_non_admin(self, mock_send_mail):
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
