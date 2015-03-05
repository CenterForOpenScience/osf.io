# -*- coding: utf-8 -*-
from nose.tools import *  # noqa
from modularodm import Q
from framework.guid.model import Guid
from tests.base import OsfTestCase
from website.project.model import Node
from tests.factories import NodeFactory

from scripts.find_guids_without_referents import get_targets


class TestFindGuidsWithoutReferents(OsfTestCase):

    def setUp(self):
        super(TestFindGuidsWithoutReferents, self).setUp()
        self.node = NodeFactory()
        self.nontarget_guid = Guid(referent=self.node)
        self.nontarget_guid.save()

    def test_get_targets_referent_is_none(self):
        bad_guid = Guid(referent=None)
        bad_guid.save()

        targets = list(get_targets())
        assert_in(bad_guid, targets)
        assert_not_in(self.nontarget_guid, targets)

    def test_get_targets_referent_points_to_nothing(self):
        node = NodeFactory()
        bad_guid = Guid(referent=node)
        bad_guid.save()
        Node.remove(Q('_id', 'eq', node._id))

        targets = list(get_targets())
        assert_in(bad_guid, targets)
        assert_not_in(self.nontarget_guid, targets)
