#!/usr/bin/env python
# encoding: utf-8
"""Find all nodes with different sets of keys for `files_current` and
`files_versions`, and ensure that all keys present in the former are also
present in the latter.


NOTE: This is a one-time migration.

Log:

    Run by sloria on production on 2014-10-16 at 16:00 EST. 15 nodes were migrated
    which include only the RPP and forks of the RPP, as expected. Verified that the
    affected files are now accessible.
"""

from website.models import Node
from website.app import init_app


def find_file_mismatch_nodes():
    """Find nodes with inconsistent `files_current` and `files_versions` field
    keys.
    """
    return [
        node for node in Node.find()
        if set(node.files_versions.keys()) != set(node.files_current.keys())
    ]


def migrate_node(node):
    """Ensure that all keys present in `files_current` are also present in
    `files_versions`.
    """
    for key, file_id in node.files_current.iteritems():
        if key not in node.files_versions:
            node.files_versions[key] = [file_id]
        else:
            if file_id not in node.files_versions[key]:
                node.files_versions[key].append(file_id)
    node.save()


def main(dry_run=True):
    init_app()
    nodes = find_file_mismatch_nodes()
    print('Migrating {0} nodes'.format(len(nodes)))
    if dry_run:
        return
    for node in nodes:
        migrate_node(node)


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv
    main(dry_run=dry_run)


from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from framework.auth import Auth


class TestMigrateFiles(OsfTestCase):

    def clear(self):
        Node.remove()

    def setUp(self):
        super(TestMigrateFiles, self).setUp()
        self.clear()
        self.nodes = []
        for idx in range(3):
            node = ProjectFactory()
            node.add_file(
                Auth(user=node.creator),
                'name',
                'contents',
                len('contents'),
                'text/plain',
            )
            self.nodes.append(node)
        self.nodes[-1].files_versions = {}
        self.nodes[-1].save()
        # Sanity check
        assert_in('name', self.nodes[-1].files_current)
        assert_not_in('name', self.nodes[-1].files_versions)

    def tearDown(self):
        super(TestMigrateFiles, self).tearDown()
        self.clear()

    def test_get_targets(self):
        targets = find_file_mismatch_nodes()
        assert_equal(len(targets), 1)
        assert_equal(targets[0], self.nodes[-1])

    def test_migrate(self):
        main(dry_run=False)
        assert_equal(len(find_file_mismatch_nodes()), 0)
        assert_in('name', self.nodes[-1].files_versions)
        assert_equal(
            self.nodes[-1].files_current['name'],
            self.nodes[-1].files_versions['name'][0],
        )
