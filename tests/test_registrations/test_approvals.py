"""Tests related to embargoes of registrations"""
import datetime
import httplib as http
import json

from modularodm import Q

import mock
from nose.tools import *  # noqa
from tests.base import fake, OsfTestCase
from tests.factories import (
    AuthUserFactory, EmbargoFactory, NodeFactory, ProjectFactory,
    RegistrationFactory, UserFactory, UnconfirmedUserFactory, DraftRegistrationFactory
)

from framework.exceptions import PermissionsError
from modularodm.exceptions import ValidationValueError
from website.exceptions import (
    InvalidSanctionRejectionToken, InvalidSanctionApprovalToken, NodeStateError,
)
from website import tokens
from website.models import Embargo, Node
from website.project.model import ensure_schemas


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
        self.valid_embargo_end_date = datetime.datetime.utcnow() + datetime.timedelta(days=3)

