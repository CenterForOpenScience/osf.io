"""Tests related to embargoes of registrations"""
import datetime

from django.utils import timezone

from nose.tools import *  # noqa
from tests.base import OsfTestCase
from osf_tests.factories import (
    AuthUserFactory, EmbargoFactory, NodeFactory, ProjectFactory,
    RegistrationFactory, UserFactory, UnconfirmedUserFactory, DraftRegistrationFactory
)

from framework.exceptions import PermissionsError
from modularodm.exceptions import ValidationValueError
from website.exceptions import (
    InvalidSanctionRejectionToken, InvalidSanctionApprovalToken, NodeStateError,
)
from website import tokens


DUMMY_TOKEN = tokens.encode({
    'dummy': 'token'
})


class DraftRegistrationApprovalTestCase(OsfTestCase):

    def setUp(self):
        super(RegistrationEmbargoModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.draft = DraftRegistrationFactory(
            branched_from=self.project,
            initiator=self.user
        )
        self.registration = RegistrationFactory(project=self.project)
        self.embargo = EmbargoFactory(user=self.user)
        self.valid_embargo_end_date = timezone.now() + datetime.timedelta(days=3)

