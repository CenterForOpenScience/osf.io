#!/usr/bin/env python
# encoding: utf-8
"""Verify that all `OsfStorageFileVersion` records created earlier than two
days before the latest inventory report are contained in the inventory, point
to the correct Glacier archive, and have an archive of the correct size.
"""

import logging

from modularodm import Q
from boto.glacier.layer2 import Layer2
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

from website.addons.osfstorage import model

from scripts import utils as scripts_utils
from scripts.osfstorage import settings as storage_settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Glacier inventories take about four hours to generate and reflect files added
# about a day before the request is made; only check records created over two
# days before the job.
DELTA_DATE = relativedelta(days=2)


class AuditError(Exception):
    pass


class NotFound(AuditError):
    pass


class BadSize(AuditError):
    pass


class BadArchiveId(AuditError):
    pass


def get_vault(credentials, settings):
    layer2 = Layer2(
        aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
        aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
    )
    return layer2.get_vault(storage_settings.GLACIER_VAULT)


def get_job(vault, job_id=None):
    if job_id:
        return vault.get_job(job_id)
    jobs = vault.list_jobs(completed=True)
    if not jobs:
        raise
    return sorted(jobs, key=lambda job: job.creation_date)[-1]


def get_targets(date):
    return model.OsfStorageFileVersion.find(
        Q('date_created', 'lt', date - DELTA_DATE)
    )


def check_glacier_version(version, inventory):
    data = inventory.get(version.location_hash)
    if data is None:
        raise NotFound('Glacier archive for version {} not found'.format(version._id))
    if version.metadata['archive'] != data['ArchiveId']:
        raise BadArchiveId(
            'Glacier archive for version {} has incorrect archive ID {} (expected {})'.format(
                version._id,
                data['ArchiveId'],
                version.metadata['archive'],
            )
        )
    if version.size != data['Size']:
        raise BadSize(
            'Glacier archive for version {} has incorrect size {} (expected {})'.format(
                version._id,
                data['Size'],
                version.size,
            )
        )


def main(job_id=None):
    job = get_job(job_id=job_id)
    output = job.get_output()
    date = parse_date(job.creation_date)
    inventory = {
        each['ArchiveDescription']: each
        for each in output['ArchiveList']
    }
    for version in get_targets(date):
        try:
            check_glacier_version(version, inventory)
        except AuditError as error:
            logger.error(str(error))


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    try:
        job_id = sys.argv[2]
    except IndexError:
        job_id = None
    main(job_id=job_id)


from nose.tools import *  # noqa

from tests.base import OsfTestCase

from website.addons.osfstorage.tests.factories import FileVersionFactory


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
        check_glacier_version(version, mock_inventory)

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
        with assert_raises(NotFound):
            check_glacier_version(version, mock_inventory)

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
        with assert_raises(BadArchiveId):
            check_glacier_version(version, mock_inventory)

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
        with assert_raises(BadSize):
            check_glacier_version(version, mock_inventory)
