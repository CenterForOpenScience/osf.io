# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import OsfTestCase

from addons.osfstorage.tests.factories import FileVersionFactory

from addons.osfstorage import model

from scripts.osfstorage import glacier_audit


mock_output = {
    'ArchiveList': [
        {
            'ArchiveDescription': 'abcdef',
            'ArchiveId': '123456',
            'Size': 24601,
        },
    ],
}
mock_inventory = {
    each['ArchiveDescription']: each
    for each in mock_output['ArchiveList']
}


class TestGlacierInventory(OsfTestCase):

    def tearDown(self):
        super(TestGlacierInventory, self).tearDown()
        model.OsfStorageFileVersion.remove()

    def test_inventory(self):
        version = FileVersionFactory(
            size=24601,
            metadata={'archive': '123456'},
            location={
                'service': 'cloud',
                'container': 'cloud',
                'object': 'abcdef',
            },
        )
        glacier_audit.check_glacier_version(version, mock_inventory)

    def test_inventory_not_found(self):
        version = FileVersionFactory(
            size=24601,
            metadata={'archive': '123456'},
            location={
                'service': 'cloud',
                'container': 'cloud',
                'object': 'abcdefg',
            },
        )
        with assert_raises(glacier_audit.NotFound):
            glacier_audit.check_glacier_version(version, mock_inventory)

    def test_inventory_wrong_archive_id(self):
        version = FileVersionFactory(
            size=24601,
            metadata={'archive': '1234567'},
            location={
                'service': 'cloud',
                'container': 'cloud',
                'object': 'abcdef',
            },
        )
        with assert_raises(glacier_audit.BadArchiveId):
            glacier_audit.check_glacier_version(version, mock_inventory)

    def test_inventory_wrong_size(self):
        version = FileVersionFactory(
            size=24602,
            metadata={'archive': '123456'},
            location={
                'service': 'cloud',
                'container': 'cloud',
                'object': 'abcdef',
            },
        )
        with assert_raises(glacier_audit.BadSize):
            glacier_audit.check_glacier_version(version, mock_inventory)
