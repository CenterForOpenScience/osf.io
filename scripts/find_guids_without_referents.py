"""Finds Guids that do not have referents
Guid = (id, referent=(GuidStoredObject primary key, GuidStoredObject name))
"""

from framework import Q
from framework.guid.model import Guid, GuidStoredObject
from website.app import init_app
from tests.base import OsfTestCase
from tests.factories import NodeFactory, UserFactory
from nose.tools import *


def main():
    # Set up storage backends
    init_app(routes=False)
    get_targets()


def get_targets():
    return Guid.find(Q('referent', 'eq', None))


class TestFindGuidsWithoutReferents(OsfTestCase):

    def setUp(self):
        super(TestFindGuidsWithoutReferents, self).setUp()
        node = NodeFactory()
        self.target_guid = Guid(referent=None)
        self.target_guid.save()

        self.nontarget_guid= Guid(referent=node)
        self.nontarget_guid.save()

    def test_get_targets(self):
        targets = list(get_targets())
        assert_in(self.target_guid, targets)
        assert_not_in(self.nontarget_guid, targets)
        assert_equal(len(targets), 1)

if __name__ == '__main__':
    main()