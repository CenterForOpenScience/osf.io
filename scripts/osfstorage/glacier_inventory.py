#!/usr/bin/env python
# encoding: utf-8
"""Begin retrieve inventory job on Glacier vault. Should be run in conjunction
with `glacier_audit.py`.
"""

import logging

from framework.celery_tasks import app as celery_app

from scripts import utils as scripts_utils
from scripts.osfstorage import settings as storage_settings
from scripts.osfstorage import utils as storage_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
scripts_utils.add_file_logger(logger, __file__)


def main():
    vault = storage_utils.get_glacier_resource().Vault(
        storage_settings.GLACIER_VAULT_ACCOUNT_ID,
        storage_settings.GLACIER_VAULT_NAME
    )
    job = vault.initiate_inventory_retrieval()
    logger.info('Started retrieve inventory job with id {}'.format(job.job_id))


@celery_app.task(name='scripts.osfstorage.glacier_inventory')
def run_main():
    main()
