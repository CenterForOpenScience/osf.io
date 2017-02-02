from nose.tools import *

from scripts.dataverse.migrate_study import do_migration, get_targets

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from addons.dataverse.model import AddonDataverseNodeSettings


class TestDatasetMigration(OsfTestCase):

    def setUp(self):
        super(TestDatasetMigration, self).setUp()
        self.project = ProjectFactory()
        self.project.creator.add_addon('dataverse')
        self.user_addon = self.project.creator.get_addon('dataverse')
        self.project.add_addon('dataverse', None)
        self.node_addon = self.project.get_addon('dataverse')
        self.node_addon.study_hdl = 'doi:12.3456/DVN/00003'
        self.node_addon.study = 'Example (DVN/00003)'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.save()

    def test_migration(self):

        do_migration([self.node_addon], dry=False)
        self.node_addon.reload()

        assert_equal(self.node_addon.dataset_doi, 'doi:12.3456/DVN/00003')
        assert_equal(self.node_addon.dataset, 'Example (DVN/00003)')

    def test_get_targets(self):
        AddonDataverseNodeSettings.remove()
        addons = [
            AddonDataverseNodeSettings(),
            AddonDataverseNodeSettings(study_hdl='foo'),
            AddonDataverseNodeSettings(user_settings=self.user_addon),
            AddonDataverseNodeSettings(study_hdl='foo', user_settings=self.user_addon),
        ]
        for addon in addons:
            addon.save()
        targets = get_targets()
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, addons[-1]._id)
