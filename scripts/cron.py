# -*- coding: utf-8 -*-

import os
import sys
import logging

import crontab

from website import settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def app_prefix(path):
    return os.path.join(settings.APP_PATH, path)


def ensure_item(cron, command):
    items = list(cron.find_command(command))
    return items[0] if items else cron.new(command)


def main(dry_run=True):

    cron = crontab.CronTab(user=settings.CRON_USER)

    analytics = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/analytics.sh')))
    analytics.hour.on(2)
    analytics.minute.on(0)  # Daily 2:00 a.m.

    logger.info('Updating crontab file:')
    logger.info(cron.render())

    if not dry_run:
        cron.write_to_user(settings.CRON_USER)


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run=dry_run)
