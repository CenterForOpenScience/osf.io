# -*- coding: utf-8 -*-

import mock
from datetime import datetime, timedelta
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.utils import mock_archive
from tests.factories import (
    AuthUserFactory,
    NodeFactory,
)

from framework.auth import Auth

from website.project.sanctions import Sanction, EmbargoTerminationApproval

from scripts.approve_embargo_terminations import main, get_pending_embargo_termination_requests

class TestApproveEmbargoTerminations(OsfTestCase):

    def tearDown(self):
        with mock.patch('framework.celery_tasks.handlers.queue', mock.Mock(return_value=None)):
            super(TestApproveEmbargoTerminations, self).tearDown()

    @mock.patch('website.project.sanctions.TokenApprovableSanction.ask', mock.Mock())
    def setUp(self):
        super(TestApproveEmbargoTerminations, self).setUp()
        self.user = AuthUserFactory()

        self.node = NodeFactory(creator=self.user)
        NodeFactory(
            creator=self.user,
            parent=NodeFactory(creator=self.user, parent=self.node)
        )

        # requesting termination but less than 48 hours old
        with mock_archive(self.node, embargo=True, autoapprove=True) as registration:
            registration.request_embargo_termination(auth=Auth(self.user))
            self.registration1 = registration

        # requesting termination and older than 48 hours
        with mock_archive(self.node, embargo=True, autoapprove=True) as registration:
            old_time = datetime.now() - timedelta(days=5)
            approval = registration.request_embargo_termination(auth=Auth(self.user))
            EmbargoTerminationApproval._storage[0].store.update(
                {'_id': approval._id},
                {'$set': {'initiation_date': old_time}},
            )
            self.registration2 = registration

        # requesting termination and older than 48 hours, but approved
        with mock_archive(self.node, embargo=True, autoapprove=True) as registration:
            old_time = datetime.now() - timedelta(days=5)
            approval = registration.request_embargo_termination(auth=Auth(self.user))
            EmbargoTerminationApproval._storage[0].store.update(
                {'_id': approval._id},
                {'$set': {'initiation_date': old_time}},
            )
            approval.state = Sanction.APPROVED
            approval.save()
            self.registration3 = registration

        # embargoed but not requesting termination
        with mock_archive(self.node, embargo=True, autoapprove=True) as registration:
            self.registration4 = registration

        EmbargoTerminationApproval._clear_caches()

    def test_get_pending_embargo_termination_requests_returns_only_unapproved(self):
        targets = get_pending_embargo_termination_requests()
        assert_equal(len(targets), 1)
        assert_equal(targets[0]._id, self.registration2.embargo_termination_approval._id)

    def test_main_auto_approves_embargo_termination_request(self):
        for node in self.registration2.node_and_primary_descendants():
            assert_false(node.is_public)
            assert_true(node.is_embargoed)
        main()
        for node in self.registration2.node_and_primary_descendants():
            assert_true(node.is_public)
            assert_false(node.is_embargoed)
