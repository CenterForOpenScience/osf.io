# -*- coding: utf-8 -*-

import mock
from datetime import timedelta

from django.utils import timezone
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory, NodeFactory, EmbargoTerminationApprovalFactory, RegistrationFactory, EmbargoFactory
from osf.models import Sanction, Registration

from scripts.approve_embargo_terminations import main, get_pending_embargo_termination_requests

class TestApproveEmbargoTerminations(OsfTestCase):

    def tearDown(self):
        with mock.patch('framework.celery_tasks.handlers.queue', mock.Mock(return_value=None)):
            super(TestApproveEmbargoTerminations, self).tearDown()

    @mock.patch('osf.models.sanctions.TokenApprovableSanction.ask', mock.Mock())
    def setUp(self):
        super(TestApproveEmbargoTerminations, self).setUp()
        self.user = AuthUserFactory()

        self.node = NodeFactory(creator=self.user)
        NodeFactory(
            creator=self.user,
            parent=NodeFactory(creator=self.user, parent=self.node)
        )

        # requesting termination but less than 48 hours old
        embargo_termination_approval = EmbargoTerminationApprovalFactory()
        self.registration1 = Registration.objects.get(embargo_termination_approval=embargo_termination_approval)

        # requesting termination and older than 48 hours
        old_time = timezone.now() - timedelta(days=5)
        embargo_termination_approval_2 = EmbargoTerminationApprovalFactory()
        embargo_termination_approval_2.initiation_date = old_time
        embargo_termination_approval_2.save()
        embargo_termination_approval_2.reload()
        self.registration2 = Registration.objects.get(embargo_termination_approval=embargo_termination_approval_2)

        # requesting termination and older than 48 hours, but approved
        embargo_termination_approval_3 = EmbargoTerminationApprovalFactory()
        embargo_termination_approval_3.initiation_date = old_time
        embargo_termination_approval_3.state = Sanction.APPROVED
        embargo_termination_approval_2.save()
        embargo_termination_approval_2.reload()
        self.registration3 = Registration.objects.get(embargo_termination_approval=embargo_termination_approval_3)

        # embargoed but not requesting termination
        embargo = EmbargoFactory()
        self.registration4 = RegistrationFactory(embargo=embargo)

    def test_get_pending_embargo_termination_requests_returns_only_unapproved(self):
        targets = get_pending_embargo_termination_requests()
        assert_equal(targets.count(), 1)
        assert_equal(targets.first()._id, self.registration2.embargo_termination_approval._id)

    def test_main_auto_approves_embargo_termination_request(self):
        for node in self.registration2.node_and_primary_descendants():
            assert_false(node.is_public)
            assert_true(node.is_embargoed)
        main()
        for node in self.registration2.node_and_primary_descendants():
            node.reload()
            assert_true(node.is_public)
            assert_false(node.is_embargoed)
