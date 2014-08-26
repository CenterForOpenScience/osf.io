#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fixes nodes with two copies of the files and wiki addons attached.

This script must be run from the OSF root directory for the imports to work.
::

    $ python -m scripts.consistency.fix_duplicate_addons


Performed on production by SL on 2014-08-12 at 5:10PM (EST).
"""

from nose.tools import assert_raises
from framework.auth.core import Auth
from website.app import init_app
from website.project.model import Node
from website.addons.wiki.model import AddonWikiNodeSettings
from website.addons.osffiles.model import AddonFilesNodeSettings

from tests.base import OsfTestCase
from tests.factories import ProjectFactory


CORRUPT_ADDONS = (AddonWikiNodeSettings, AddonFilesNodeSettings)

def main():
    from framework.mongo import db
    init_app(routes=False)
    do_migration(db)


def get_targets(db, addon_class):
    """Generate affected nodes."""
    query = db['node'].find({
        '.'.join(
            ('__backrefs',
                'addons',
                addon_class.__name__.lower(),
                'owner'
            )
        ): {'$size': 2}
    })
    return (Node.load(node['_id']) for node in query)


def do_migration(db):
    for addon_class in CORRUPT_ADDONS:
        print('Processing ' + addon_class.__name__)

        for node in get_targets(db, addon_class):
            print('- ' + node._id)
            backref_key = '{}__addons'.format(addon_class.__name__.lower())
            keep, discard = getattr(node, backref_key)
            addon_class.remove_one(discard)

        print('')

    print('-----\nDone.')


class TestRemovingDuplicateFileAndWikiAddons(OsfTestCase):

    def test_get_targets(self):
        bad_project = ProjectFactory()
        auth = Auth(bad_project.creator)
        bad_project.add_addon('osffiles', auth=auth)

        bad_project.add_addon('osffiles', auth=auth, _force=True)
        bad_project.save()

        good_project = ProjectFactory()
        good_project.add_addon('osffiles', auth=Auth(good_project.creator))
        good_project.save()

        targets = get_targets(self.db, AddonFilesNodeSettings)
        assert bad_project in targets
        assert good_project not in targets

    def test_do_migration(self):
        bad_project = ProjectFactory()
        auth = Auth(bad_project.creator)
        bad_project.add_addon('osffiles', auth=auth)
        bad_project.add_addon('osffiles', auth=auth, _force=True)
        bad_project.save()

        bad_project2 = ProjectFactory()
        auth2 = Auth(bad_project2.creator)
        bad_project2.add_addon('wiki', auth=auth2)
        bad_project2.add_addon('wiki', auth=auth2, _force=True)
        bad_project2.save()
        # sanity check
        with assert_raises(AssertionError):
            bad_project.get_addon('osffiles')
        with assert_raises(AssertionError):
            bad_project2.get_addon('wiki')
        do_migration(self.db)
        # no more errors
        assert isinstance(bad_project.get_addon('wiki'), AddonWikiNodeSettings)
        assert isinstance(bad_project2.get_addon('osffiles'), AddonFilesNodeSettings)


if __name__ == '__main__':
    main()
