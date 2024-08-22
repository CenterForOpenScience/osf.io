#!/usr/bin/env python3

import logging
import math
import time
from django.utils import timezone

import django
from oauthlib.oauth2 import OAuth2Error
from dateutil.relativedelta import relativedelta
django.setup()

from framework.celery_tasks import app as celery_app

from scripts import utils as scripts_utils

from website.app import init_app
from addons.box.models import Provider as Box
from addons.googledrive.models import GoogleDriveProvider
from addons.mendeley.models import Mendeley
from osf.models import ExternalAccount

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PROVIDER_CLASSES = (Box, GoogleDriveProvider, Mendeley, )


def look_up_provider(addon_short_name):
    for Provider in PROVIDER_CLASSES:
        if Provider.short_name == addon_short_name:
            return Provider
    return None

def get_targets(delta, addon_short_name):
    # NOTE: expires_at is the  access_token's expiration date,
    # NOT the refresh token's
    return ExternalAccount.objects.filter(
        expires_at__lt=timezone.now() - delta,
        date_last_refreshed__lt=timezone.now() - delta,
        provider=addon_short_name
    )

def main(delta, Provider, rate_limit, dry_run):
    allowance = rate_limit[0]
    last_call = time.time()
    for record in get_targets(delta, Provider.short_name):
        if Provider(record).has_expired_credentials:
            logger.info(
                f'Found expired record {record.__repr__()}, skipping'
            )
            continue

        logger.info(
            'Refreshing tokens on record {}; expires at {}'.format(
                record.__repr__(),
                record.expires_at.strftime('%c')
            )
        )
        if not dry_run:
            if allowance < 1:
                try:
                    time.sleep(rate_limit[1] - (time.time() - last_call))
                except (ValueError, OSError):
                    pass  # Value/IOError indicates negative sleep time in Py 3.5/2.7, respectively
                allowance = rate_limit[0]

            allowance -= 1
            last_call = time.time()
            success = False
            try:
                success = Provider(record).refresh_oauth_key(force=True)
            except OAuth2Error as e:
                logger.error(e)
            else:
                logger.info(
                    'Status of record {}: {}'.format(
                        record.__repr__(),
                        'SUCCESS' if success else 'FAILURE')
                )


@celery_app.task(name='scripts.refresh_addon_tokens')
def run_main(addons=None, rate_limit=(5, 1), dry_run=True):
    """
    :param dict addons: of form {'<addon_short_name>': int(<refresh_token validity duration in days>)}
    :param tuple rate_limit: of form (<requests>, <seconds>). Default is five per second
    """
    init_app(set_backends=True, routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    for addon in addons:
        days = math.ceil(int(addons[addon])*0.75)
        delta = relativedelta(days=days)
        Provider = look_up_provider(addon)
        if not Provider:
            logger.error(f'Unable to find Provider class for addon {addon}')
        else:
            main(delta, Provider, rate_limit, dry_run=dry_run)
