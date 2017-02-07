# -*- coding: utf-8 -*-
import datetime

from django.utils import timezone
from nose.tools import *  # noqa

from scripts.osfstorage.utils import ensure_osf_files
from website import settings
ensure_osf_files(settings)

# Hack: Must configure add-ons before importing `OsfTestCase`
from addons.osfstorage.tests.factories import FileVersionFactory
from addons.osfstorage.model import OsfStorageFileRecord
from addons.osffiles.model import NodeFile
from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from scripts.osfstorage.migrate_dates import main


class TestMigrateDates(OsfTestCase):

    def setUp(self):
        super(TestMigrateDates, self).setUp()
        self.path = 'old-pizza'
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')
        self.node_file = NodeFile(path=self.path)
        self.node_file.save()
        self.node_file.reload()
        self.date = self.node_file.date_modified
        self.project.files_versions['old_pizza'] = [self.node_file._id]
        self.project.save()
        self.version = FileVersionFactory(date_modified=timezone.now())
        self.record, _ = OsfStorageFileRecord.get_or_create(self.node_file.path, self.node_settings)
        self.record.versions = [self.version]
        self.record.save()

    def test_migrate_dates(self):
        assert_not_equal(self.version.date_modified, self.date)
        main(dry_run=False)
        assert_equal(self.version.date_created, self.date)
