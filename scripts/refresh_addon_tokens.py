#!/usr/bin/env python
# encoding: utf-8

import logging
import datetime

from modularodm import Q
from dateutil.relativedelta import relativedelta

from framework.celery_tasks import app as celery_app

from scripts import utils as scripts_utils

from website.app import init_app
from website.addons.box.model import Box
from website.addons.mendeley.model import Mendeley
from website.oauth.models import ExternalAccount
from website.addons.base.exceptions import AddonError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PROVIDER_CLASSES = (Box, Mendeley, )


def look_up_provider(addon_short_name):
    for Provider in PROVIDER_CLASSES:
        if Provider.short_name == addon_short_name:
            return Provider
    return None

def get_targets(delta, addon_short_name):
    # NOTE: expires_at is the  access_token's expiration date,
    # NOT the refresh token's
    return ExternalAccount.find(
        Q('expires_at', 'lt', datetime.datetime.utcnow() - delta) &
        Q('provider', 'eq', addon_short_name)
    )

def main(delta, Provider, dry_run):
    for record in get_targets(delta, Provider.short_name):
        logger.info(
            'Refreshing tokens on record {0}; expires at {1}'.format(
                record._id,
                record.expires_at.strftime('%c')
            )
        )
        if not dry_run:
            success = False
            try:
                success = Provider(record).refresh_oauth_key(force=True)
            except AddonError as ex:
                logger.error(ex.message)
            else:
                logger.info(
                    'Status of record {}: {}'.format(
                        record._id,
                        'SUCCESS' if success else 'FAILURE')
                )

@celery_app.task(name='scripts.refresh_addon_tokens')
def run_main(addons=None, dry_run=True):
    """
    :param dict addons: of form {'<addon_short_name>': int(<refresh_token validity duration in days>)}
    """
    init_app(set_backends=True, routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    for addon in addons:
        try:
            days = int(addons[addon])
        except (ValueError, TypeError):
            days = 7  # refresh tokens that expire this week
        delta = relativedelta(days=days)
        Provider = look_up_provider(addon)
        if not Provider:
            logger.error('Unable to find Provider class for addon {}'.format(addon_short_name))
        else:
            main(delta, Provider, dry_run=dry_run)
