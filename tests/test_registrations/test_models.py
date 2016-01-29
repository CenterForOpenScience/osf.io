# -*- coding: utf-8 -*-
"""Unit tests for models and their factories."""
from nose.tools import *  # noqa (PEP8 asserts)
import mock

from modularodm import Q

import datetime as dt

from website.models import MetaSchema, DraftRegistrationApproval
from website.settings import PREREG_ADMIN_TAG

from tests.factories import (
    UserFactory, ApiOAuth2ApplicationFactory, NodeFactory, PointerFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory,
    NodeWikiFactory, RegistrationFactory, UnregUserFactory,
    ProjectWithAddonFactory, UnconfirmedUserFactory, CommentFactory, PrivateLinkFactory,
    AuthUserFactory, DashboardFactory, FolderFactory,
    NodeLicenseRecordFactory, DraftRegistrationFactory
)
from tests.test_registrations.base import RegistrationsTestBase


class TestDraftRegistrations(RegistrationsTestBase):

    def test_factory(self):
        draft = DraftRegistrationFactory()
        assert_is_not_none(draft.branched_from)
        assert_is_not_none(draft.initiator)
        assert_is_not_none(draft.registration_schema)

        user = AuthUserFactory()
        draft = DraftRegistrationFactory(initiator=user)
        assert_equal(draft.initiator, user)

        node = ProjectFactory()
        draft = DraftRegistrationFactory(branched_from=node)
        assert_equal(draft.branched_from, node)
        assert_equal(draft.initiator, node.creator)

        # Pick an arbitrary v2 schema
        schema = MetaSchema.find(
            Q('schema_version', 'eq', 2)
        )[0]
        data = {'some': 'data'}
        draft = DraftRegistrationFactory(registration_schema=schema, registration_metadata=data)
        assert_equal(draft.registration_schema, schema)
        assert_equal(draft.registration_metadata, data)

    @mock.patch('website.project.model.Node.register_node')
    def test_register(self, mock_register_node):

        self.draft.register(self.auth)
        mock_register_node.assert_called_with(
            schema=self.draft.registration_schema,
            auth=self.auth,
            data=self.draft.registration_metadata,
        )

    def test_update_metadata_tracks_changes(self):
        self.draft.registration_metadata = {
            'foo': {
                'value': 'bar',
            },
            'a': {
                'value': 1,
            },
            'b': {
                'value': True
            },
        }
        changes =  self.draft.update_metadata({
            'foo': {
                'value': 'foobar',
            },
            'a': {
                'value': 1,
            },
            'b': {
                'value': True,
            },
            'c': {
                'value': 2,
            },
        })
        self.draft.save()
        for key in ['foo', 'c']:
            assert_in(key, changes)

    def test_update_metadata_interleaves_comments_by_created_timestamp(self):
        now = dt.datetime.today()

        comments = []
        times = (now + dt.timedelta(minutes=i) for i in range(6))
        for time in times:
            comments.append({
                'created': time.isoformat(),
                'value': 'Foo'
            })
        orig_data = {
            'foo': {
                'value': 'bar',
                'comments': [comments[i] for i in range(0, 6, 2)]
            }
        }
        self.draft.update_metadata(orig_data)
        self.draft.save()
        assert_equal(
            self.draft.registration_metadata['foo']['comments'],
            [comments[i] for i in range(0, 6, 2)]
        )
        new_data = {
            'foo': {
                'value': 'bar',
                'comments': [comments[i] for i in range(1, 6, 2)]
            }
        }
        self.draft.update_metadata(new_data)
        self.draft.save()
        assert_equal(
            self.draft.registration_metadata['foo']['comments'],
            comments,
        )


class TestDraftRegistrationApprovals(RegistrationsTestBase):

    def setUp(self):
        super(TestDraftRegistrationApprovals, self).setUp()
        self.approval = DraftRegistrationApproval(
            initiated_by=self.user,
            meta={
                'registration_choice': 'immediate'
            }
        )
        self.authorizer1 = AuthUserFactory()
        self.authorizer2 = AuthUserFactory()
        self.approval.save()
        self.draft.registration_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        self.draft.approval = self.approval
        self.draft.save()

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_on_complete_immediate_creates_registration_for_draft_initiator(self, mock_enquque):
        self.approval._on_complete(self.user)

        registered_node = self.draft.registered_node
        assert_is_not_none(registered_node)
        assert_true(registered_node.is_pending_registration)
        assert_equal(registered_node.registered_user, self.draft.initiator)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_on_complete_embargo_creates_registration_for_draft_initiator(self, mock_enquque):
        end_date = dt.datetime.now() + dt.timedelta(days=366)  # <- leap year
        self.approval = DraftRegistrationApproval(
            initiated_by=self.user,
            meta={
                'registration_choice': 'embargo',
                'embargo_end_date': end_date.isoformat()
            }
        )
        self.authorizer1 = AuthUserFactory()
        self.authorizer2 = AuthUserFactory()
        self.approval.save()
        self.draft.approval = self.approval
        self.draft.save()

        self.approval._on_complete(self.user)
        registered_node = self.draft.registered_node
        assert_is_not_none(registered_node)
        assert_true(registered_node.is_pending_embargo)
        assert_equal(registered_node.registered_user, self.draft.initiator)

    def test_approval_requires_only_a_single_authorizer(self):
        with mock.patch.object(self.approval, '_on_complete') as mock_on_complete:
            self.authorizer1.system_tags.append(PREREG_ADMIN_TAG)
            self.approval.approve(self.authorizer1)
            assert_true(mock_on_complete.called)
            assert_true(self.approval.is_approved)

    @mock.patch('website.mails.send_mail')
    def test_on_reject(self, mock_send_mail):
        self.approval._on_reject(self.user)
        assert_equal(self.approval.meta, {})
        assert_true(mock_send_mail.called_once)
