#!/usr/bin/env python
# encoding: utf-8
"""Begin retrieve inventory job on Glacier vault. Should be run in conjunction
with `glacier_audit.py`.
"""

import logging
import datetime

from boto.glacier.layer2 import Layer2

from framework.celery_tasks import app as celery_app

from scripts import utils as scripts_utils
from scripts.osfstorage import settings as storage_settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
scripts_utils.add_file_logger(logger, __file__)


def get_vault():
    layer2 = Layer2(
        aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
        aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
    )
    return layer2.get_vault(storage_settings.GLACIER_VAULT)


def main():
    vault = get_vault()
    job = vault.retrieve_inventory_job(
        description='glacier-audit-{}'.format(datetime.datetime.utcnow().strftime('%c')),
        sns_topic=storage_settings.AWS_SNS_ARN,
    )
    logger.info('Started retrieve inventory job with id {}'.format(job.id))


@celery_app.task(name='scripts.osfstorage.glacier_inventory')
def run_main():
    main()
