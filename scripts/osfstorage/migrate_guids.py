#!/usr/bin/env python
# encoding: utf-8
"""For each `OsfGuidFile` record, create a corresponding `OsfStorageGuidFile`
record with the same `_id`, `node`, and `path` fields; find the associated `Guid`
record, and set its `referent` to the newly created record.
"""

import logging

from modularodm import Q
from modularodm import exceptions as modm_errors

from framework.transactions.context import TokuTransaction

from website import settings
from website.models import Guid
from website.app import init_app

from website.addons.osffiles.model import OsfGuidFile
from website.addons.osfstorage.model import OsfStorageGuidFile

from scripts import utils as script_utils
from scripts.osfstorage.utils import ensure_osf_files


logger = logging.getLogger(__name__)
script_utils.add_file_logger(logger, __file__)
logging.basicConfig(level=logging.INFO)


def get_or_create_storage_file(node, path, **kwargs):
    """Get or create `OsfStorageGuidFile` record. Used instead of
    `OsfStorageGuidFile#get_or_create` to permit setting additional fields on
    the created object.
    """
    try:
        return OsfStorageGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', path)
        )
    except modm_errors.ModularOdmException as error:
        obj = OsfStorageGuidFile(node=node, path=path, **kwargs)
        obj.save()
    return obj


def migrate_legacy_obj(legacy_guid_file):
    """Create `OsfStorageGuidFile` object corresponding to provided `OsfGuidFile`
    object, then set the `referent` of the `Guid` object to the newly created
    record.
    """
    logger.info('Migrating legacy Guid {0}'.format(legacy_guid_file._id))
    storage_obj = get_or_create_storage_file(
        legacy_guid_file.node,
        legacy_guid_file.name,
        _id=legacy_guid_file._id,
    )
    guid_obj = Guid.load(legacy_guid_file._id)
    guid_obj.referent = storage_obj
    guid_obj.save()

    return storage_obj


def find_legacy_objs():
    return OsfGuidFile.find()


def main(dry_run=True):
    legacy_objs = find_legacy_objs()
    logger.info('Migrating {0} `OsfGuidFile` objects'.format(legacy_objs.count()))
    if dry_run:
        return
    for legacy_obj in legacy_objs:
        with TokuTransaction():
            migrate_legacy_obj(legacy_obj)


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv
    ensure_osf_files(settings)
    init_app(set_backends=True, routes=False)
    main(dry_run=dry_run)


# Hack: Must configure add-ons before importing `OsfTestCase`
ensure_osf_files(settings)

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory


class TestMigrateGuids(OsfTestCase):

    def clear_guids(self):
        OsfGuidFile.remove()
        OsfStorageGuidFile.remove()

    def setUp(self):
        super(TestMigrateGuids, self).setUp()
        self.clear_guids()
        self.project = ProjectFactory()
        self.paths = ['peppers', 'sausage', 'pepperoni']
        self.legacy_objs = [
            OsfGuidFile(node=self.project, name=path)
            for path in self.paths
        ]
        for obj in self.legacy_objs:
            obj.save()

    def tearDown(self):
        self.clear_guids()

    def test_find_targets(self):
        legacy_objs = find_legacy_objs()
        assert_equal(set(legacy_objs), set(self.legacy_objs))

    def test_migrate(self):
        # Sanity check
        for obj in self.legacy_objs:
            guid_obj = Guid.load(obj._id)
            assert_equal(guid_obj.referent, obj)
        nobjs = OsfStorageGuidFile.find().count()
        main(dry_run=False)
        Guid._clear_caches()
        for obj in self.legacy_objs:
            guid_obj = Guid.load(obj._id)
            assert_not_equal(guid_obj.referent, obj)
            assert_true(isinstance(guid_obj.referent, OsfStorageGuidFile))
            assert_equal(guid_obj.referent.node, self.project)
            assert_equal(guid_obj.referent.path, obj.name)
            assert_equal(guid_obj.referent._id, obj._id)
        assert_equal(OsfStorageGuidFile.find().count(), nobjs + 3)
        # Test idempotence
        main(dry_run=False)
        assert_equal(OsfStorageGuidFile.find().count(), nobjs + 3)
