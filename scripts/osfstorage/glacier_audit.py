#!/usr/bin/env python
# encoding: utf-8
"""Verify that all `OsfStorageFileVersion` records created earlier than two
days before the latest inventory report are contained in the inventory, point
to the correct Glacier archive, and have an archive of the correct size.
Should be run after `glacier_inventory.py`.
"""

import logging

from modularodm import Q
from boto.glacier.layer2 import Layer2
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

from framework.celery_tasks import app as celery_app

from website.app import init_app
from website.files import models

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


def get_vault():
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
        raise RuntimeError('No completed jobs found')
    return sorted(jobs, key=lambda job: job.creation_date)[-1]


def get_targets(date):
    return models.FileVersion.find(
        Q('date_created', 'lt', date - DELTA_DATE) &
        Q('status', 'ne', 'cached') &
        Q('metadata.archive', 'exists', True) &
        Q('location', 'ne', None)
    )


def check_glacier_version(version, inventory):
    data = inventory.get(version.metadata['archive'])
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
    if (version.size or version.metadata.get('size')) != data['Size']:
        raise BadSize(
            'Glacier archive for version {} has incorrect size {} (expected {})'.format(
                version._id,
                data['Size'],
                version.size,
            )
        )


def main(job_id=None):
    vault = get_vault()
    job = get_job(vault, job_id=job_id)
    output = job.get_output()
    date = parse_date(job.creation_date)
    inventory = {
        each['ArchiveId']: each
        for each in output['ArchiveList']
    }
    for version in get_targets(date):
        try:
            check_glacier_version(version, inventory)
        except AuditError as error:
            logger.error(str(error))


@celery_app.task(name='scripts.osfstorage.glacier_audit')
def run_main(job_id=None, dry_run=True):
    init_app(set_backends=True, routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(job_id=job_id)
