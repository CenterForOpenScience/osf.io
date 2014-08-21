"""Finds Guids do not have referents"""

from framework import Q
from framework.guid.model import Guid
from website.app import init_app
from tests.base import OsfTestCase
from tests.factories import NodeFactory


QUERY = Q('referent', 'eq', 'null')

#referent = ('node', 'asd87k')


def main():
    # Set up storage backends
    init_app(routes=False)
    get_targets()


def get_targets():
    node = NodeFactory()
    g = Guid.find(Q('referent', 'eq', None)) #Guids with no referents -->
    for guid in g:
        print guid._id
        #print guid.referent



class TestFindGuidsWithoutReferents(OsfTestCase):

    def setUp(self):
        super(TestFindGuidsWithoutReferents, self).setUp()
        node = NodeFactory()
        self.target_guid = Guid(referent=None)
        print self.target_guid._id
        print self.target_guid.referent
        self.nontarget_guid= Guid(referent=node)
        #print self.nontarget_guid._id

        self.nontarget_guid.save()

    def test_get_targets(self):
        get_targets()
        assert_equal()

        #print Guid.find(Q('referent', 'eq', None))

if __name__ == '__main__':
    main()