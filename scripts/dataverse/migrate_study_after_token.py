#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to migrate dataverse projects to accomodate changes in their 4.0 API.
This assumes that the script `migrate_credentials_to_token` has been run.

Changes:
 - Rename node_addon.study to node_addon.dataset
 - Rename node_addon.study_hdl to node_addon.dataset_doi
 - Generate node_addon.dataset_id from existing credentials/doi

"""

import logging
from modularodm import Q

import mock
from nose.tools import *
from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.app import init_app
from scripts import utils as script_utils

from website.addons.dataverse import client
from website.addons.dataverse.model import AddonDataverseNodeSettings
from website.addons.dataverse.tests.utils import create_mock_connection

logger = logging.getLogger(__name__)


def do_migration(records, dry=True):
    for node_addon in records:

        logger.info('Record found for dataset {}'.format(node_addon.study_hdl))

        # Generate dataset id / updated title
        connection = client.connect_from_settings(node_addon.user_settings)
        dataverse = client.get_dataverse(connection, node_addon.dataverse_alias)
        dataset = client.get_dataset(dataverse, node_addon.study_hdl)

        logger.info('setting ID to {}'.format(dataset.id))

        if not dry:
            node_addon.dataset_doi = node_addon.study_hdl
            node_addon.dataset_id = dataset.id
            node_addon.dataset = dataset.title

            node_addon.study_hdl = None
            node_addon.study = None

            node_addon.save()


def get_targets():
    return AddonDataverseNodeSettings.find(
        Q('user_settings', 'ne', None) &
        Q('study_hdl', 'ne', None)
    )


def main(dry=True):
    init_app(set_backends=True, routes=False, mfr=False)  # Sets the storage backends on all models
    do_migration(get_targets(), dry=dry)


class TestDatasetMigration(OsfTestCase):

    def setUp(self):
        super(TestDatasetMigration, self).setUp()
        self.project = ProjectFactory()
        self.project.creator.add_addon('dataverse')
        self.user_addon = self.project.creator.get_addon('dataverse')
        self.project.add_addon('dataverse', None)
        self.node_addon = self.project.get_addon('dataverse')
        self.node_addon.dataverse_alias = 'DVN/00002'
        self.node_addon.study_hdl = 'doi:12.3456/DVN/00003'
        self.node_addon.study = 'Example (DVN/00003)'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.save()

    @mock.patch('website.addons.dataverse.client.connect_from_settings')
    def test_migration(self, mock_connect):
        mock_connect.return_value = create_mock_connection()

        do_migration([self.node_addon], dry=False)
        self.node_addon.reload()

        assert_equal(self.node_addon.dataset_doi, 'doi:12.3456/DVN/00003')
        assert_equal(self.node_addon.dataset, 'Example (DVN/00003)')
        assert_equal(self.node_addon.dataset_id, '18')

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


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)