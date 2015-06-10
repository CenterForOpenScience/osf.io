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
    analytics.hour.on(2)  # 2 a.m.

    digest = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/send_digest.sh')))
    digest.hour.on(2)  # 2 a.m.

    box = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/refresh_box_tokens.sh')))
    box.hour.on(2)  # 2 a.m.

    retractions = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/retract_registrations.sh')))
    retractions.hour.on(0)  # 12 a.m.

    embargoes = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/embargo_registrations.sh')))
    embargoes.hours.on(0)   # 12 a.m.

    files_audit = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/files_audit.sh')))
    files_audit.hour.on(2)  # 2 a.m.

    glacier_inventory = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/glacier_inventory.sh')))
    glacier_inventory.hour.on(0)  # 12 a.m.

    glacier_audit = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/glacier_audit.sh')))
    glacier_audit.hour.on(6)  # 6 a.m.

    logger.info('Updating crontab file:')
    logger.info(cron.render())

    if not dry_run:
        cron.write_to_user(settings.CRON_USER)


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run=dry_run)
