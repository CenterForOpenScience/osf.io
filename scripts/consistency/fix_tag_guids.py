"""Removes legacy Tag objects from the Guid namespace.

Tags were once GuidStoredObjects, but are no longer. The Guid table was not
cleaned of these references.

This caused a specific issue where "project" was a Tag id, and therefore was
resolveable to a Guid object, thereby breaking our routing system for URLs
beginning with /project/.

This script must be run from the OSF root directory for the imports to work.
::

    $ python -m scripts.consistency.fix_tag_guids dry
    $ python -m scripts.consistency.fix_tag_guids

Log:

    Performed on production by sloria on 2014-08-15 at 11.45AM. 892 invalid GUID
    objects were removed.
"""
import sys

from nose.tools import *  # noqa

from framework import Q
from framework.guid.model import Guid
from website.app import init_app

from tests.base import OsfTestCase
from tests.factories import TagFactory, NodeFactory

QUERY = Q('referent.1', 'eq', "tag")

def main():
    # Set up storage backends
    init_app(routes=False)
    targets = get_targets()
    if 'dry' in sys.argv:
        print('{n} invalid GUID objects will be removed.'.format(n=targets.count()))
        sys.exit(0)
    else:
        do_migration()
        if get_targets().count() == 0:
            print('All invalid references removed.')
        else:
            print('Failed to remove all references.')
            sys.exit(1)

def do_migration():
    Guid.remove(QUERY)

def get_targets():
    return Guid.find(QUERY)

class TestMigrateLegacyTagGUIDObjects(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        tag = TagFactory()
        self.target_guid = Guid(referent=tag)
        self.target_guid.save()
        self.nontarget_guid = Guid(referent=NodeFactory())

    def test_get_targets(self):
        result = list(get_targets())
        assert_in(self.target_guid, result)
        assert_not_in(self.nontarget_guid, result)

    def test_do_migration(self):
        # sanity check
        assert_equal(len(list(get_targets())), 1)
        do_migration()
        assert_equal(len(list(get_targets())), 0)

if __name__ == '__main__':
    main()
