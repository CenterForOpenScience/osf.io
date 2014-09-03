"""Finds Guids that do not have referents or that point to referents that no longer exist.

E.g. a node was created and given a guid but an error caused the node to
get deleted, leaving behind a guid that points to nothing.
"""

from framework import Q
from framework.guid.model import Guid
from website.app import init_app
from website.project.model import Node
from tests.base import OsfTestCase
from tests.factories import NodeFactory
from nose.tools import *


def main():
    # Set up storage backends
    init_app(routes=False)
    print ('{n} invalid GUID objects found'.format(n=len(get_targets())))


def get_targets():
    """Find GUIDs with no referents and GUIDs with referents that no longer exist."""
    # Use a list comp because querying MODM with Guid.find(Q('referent', 'eq', None))
    # only catches the first case.
    return [each for each in Guid.find() if each.referent is None]


class TestFindGuidsWithoutReferents(OsfTestCase):

    def setUp(self):
        super(TestFindGuidsWithoutReferents, self).setUp()
        self.node = NodeFactory()
        self.nontarget_guid= Guid(referent=self.node)
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


if __name__ == '__main__':
    main()