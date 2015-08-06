# -*- coding: utf-8 -*-
from flask import g
import mock
import unittest
from nose.tools import *  # noqa (PEP8 asserts)

import datetime
from modularodm import fields, storage

from tests.base import OsfTestCase
from tests import factories

from framework.mongo import handlers

from website.project.model import Sanction, EmailApprovableSanction

def valid_user():
    return factories.UserFactory(system_tags=['flag'])

class SanctionTestClass(Sanction):

    DISPLAY_NAME = 'test class'

    initiated_by = fields.ForeignField('user', backref='tested')

    def _validate_authorizer(self, user):
        return 'flag' in user.system_tags

class EmailApprovableSanctionTestClass(EmailApprovableSanction):

    AUTHORIZER_NOTIFY_TEMPLATE = 'authorizer'
    NON_AUTHORIZER_NOTIFY_TEMPLATE = 'non-authorizer'


class SanctionsTestCase(OsfTestCase):

    def setUp(self, *args, **kwargs):
        super(SanctionsTestCase, self).setUp(*args, **kwargs)
        handlers.set_up_storage([
            SanctionTestClass,
            EmailApprovableSanctionTestClass
        ], storage.MongoStorage)

class TestSanction(SanctionsTestCase):

    def setUp(self, *args, **kwargs):
        super(TestSanction, self).setUp(*args, **kwargs)
        self.user = valid_user()
        self.invalid_user = factories.UserFactory()
        self.sanction = SanctionTestClass(
            initiated_by=self.user,
            end_date=datetime.datetime.now() + datetime.timedelta(days=2)
        )
        self.sanction.add_authorizer(self.user, save=True)

    def test_pending_approval(self):
        assert_true(self.sanction.pending_approval)
        self.sanction.state = Sanction.ACTIVE
        assert_false(self.sanction.pending_approval)

    def test_validate_authorizer(self):
        assert_false(self.sanction._validate_authorizer(self.invalid_user))
        assert_true(self.sanction._validate_authorizer(self.user))

    def test_add_authorizer(self):
        new_user = valid_user()
        added = self.sanction.add_authorizer(new_user)
        assert_true(added)
        assert_in(new_user._id, self.sanction.approval_state.keys())
        assert_in('approval_token', self.sanction.approval_state[new_user._id])
        assert_in('rejection_token', self.sanction.approval_state[new_user._id])

    def test_add_authorizer_already_added(self):
        added = self.sanction.add_authorizer(self.user)
        assert_false(added)
        assert_in(self.user._id, self.sanction.approval_state.keys())

    def test_add_authorizer_invalid(self):
        invalid_user = factories.UserFactory()
        added = self.sanction.add_authorizer(invalid_user)
        assert_false(added)
        assert_not_in(invalid_user._id, self.sanction.approval_state.keys())

    def test_remove_authorizer(self):
        removed = self.sanction.remove_authorizer(self.user)
        assert_true(removed)
        assert_not_in(self.user._id, self.sanction.approval_state.keys())

    def test_remove_authorizer_not_added(self):
        not_added = factories.UserFactory()
        removed = self.sanction.remove_authorizer(not_added)
        assert_false(removed)
        assert_not_in(not_added, self.sanction.approval_state.keys())

    @mock.patch.object(SanctionTestClass, '_on_complete')
    def test_on_approve_incomplete(self, mock_complete):
        another_user = valid_user()
        self.sanction.add_authorizer(another_user, approved=True)
        self.sanction._on_approve(self.user, '')
        assert_false(mock_complete.called)

    @mock.patch.object(SanctionTestClass, '_on_complete')
    def test_on_approve_complete(self, mock_complete):
        self.sanction.approval_state[self.user._id]['has_approved'] = True
        self.sanction._on_approve(self.user, '')
        assert_true(mock_complete.called)

    @mock.patch.object(SanctionTestClass, '_on_complete')
    def test_on_approve_complete(self, mock_complete):
        self.sanction.approval_state[self.user._id]['has_approved'] = True
        self.sanction._on_approve(self.user, '')
        assert_true(mock_complete.called)

    def test_on_reject_raises_NotImplementedError(self):
        err = lambda: self.sanction._on_reject(self.user, '')
        assert_raises(NotImplementedError, err)

    def test_on_complete_raises_NotImplementedError(self):
        err = lambda: self.sanction._on_complete(self.user)
        assert_raises(NotImplementedError, err)

    @mock.patch.object(SanctionTestClass, '_on_approve')
    def test_approve(self, mock_on_approve):
        approval_token = self.sanction.approval_state[self.user._id]['approval_token']
        self.sanction.approve(self.user, approval_token)
        assert_true(self.sanction.approval_state[self.user._id]['has_approved'])
        assert_true(mock_on_approve.called)

    @mock.patch.object(SanctionTestClass, '_on_reject')
    def test_reject(self, mock_on_reject):
        rejection_token = self.sanction.approval_state[self.user._id]['rejection_token']
        self.sanction.reject(self.user, rejection_token)
        assert_false(self.sanction.approval_state[self.user._id]['has_approved'])
        assert_true(mock_on_reject.called)

    @mock.patch.object(SanctionTestClass, '_notify_authorizer')
    @mock.patch.object(SanctionTestClass, '_notify_non_authorizer')
    def test_ask(self, mock_notify_non_authorizer, mock_notify_authorizer):
        other_user = factories.UserFactory()
        group = [other_user, self.user]
        self.sanction.ask(group)
        assert_true(mock_notify_non_authorizer.called_once_with(other_user))
        assert_true(mock_notify_authorizer.called_once_with(self.user))

class TestEmailApprovableSanction(SanctionsTestCase):

    def setUp(self, *args, **kwargs):
        super(TestEmailApprovableSanction, self).setUp(*args, **kwargs)
        self.user = factories.UserFactory()
        self.sanction = EmailApprovableSanctionTestClass(
            initiated_by=self.user,
            end_date=datetime.datetime.now() + datetime.timedelta(days=2)
        )
        self.sanction.add_authorizer(self.user)

    def test_format_or_empty(self):
        context = {
            'key': 'value'
        }
        template = 'What a good {key}'
        assert_equal(EmailApprovableSanctionTestClass._format_or_empty(template, context), 'What a good value')

    def test_format_or_empty_empty(self):
        context = None
        template = 'What a good {key}'
        assert_equal(EmailApprovableSanctionTestClass._format_or_empty(template, context), '')

    @mock.patch.object(EmailApprovableSanctionTestClass, '_send_approval_request_email')
    @mock.patch.object(EmailApprovableSanctionTestClass, '_email_template_context')
    def test_notify_authorizer(self, mock_get_email_template_context, mock_send_approval_email):
        mock_get_email_template_context.return_value = 'context'
        self.sanction._notify_authorizer(self.user)
        assert_true(mock_get_email_template_context.called_once_with(self.user, True))
        assert_true(mock_send_approval_email.called_once_with(self.user, 'authorizer', 'context'))

    @mock.patch.object(EmailApprovableSanctionTestClass, '_send_approval_request_email')
    @mock.patch.object(EmailApprovableSanctionTestClass, '_email_template_context')
    def test_notify_non_authorizer(self, mock_get_email_template_context, mock_send_approval_email):
        mock_get_email_template_context.return_value = 'context'
        other_user = factories.UserFactory()
        self.sanction._notify_non_authorizer(other_user)
        assert_true(mock_get_email_template_context.called_once_with(other_user, False))
        assert_true(mock_send_approval_email.called_once_with(other_user, 'non-authorizer', 'context'))

    def test_add_authorizer(self):
        assert_is_not_none(self.sanction.stashed_urls.get(self.user._id))
