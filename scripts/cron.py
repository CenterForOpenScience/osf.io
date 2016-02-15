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

    box = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/refresh_box_tokens.sh')))
    box.hour.on(2)
    box.minute.on(0)  # Daily 2:00 a.m.

    retractions = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/retract_registrations.sh')))
    retractions.hour.on(0)
    retractions.minute.on(0)  # Daily 12 a.m.

    embargoes = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/embargo_registrations.sh')))
    embargoes.hour.on(0)
    embargoes.minute.on(0)  # Daily 12 a.m.

    registration_approvals = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/approve_registrations.sh')))
    registration_approvals.hour.on(0)
    registration_approvals.minute.on(0)  # Daily 12 a.m.

    files_audit = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/files_audit.sh')))
    files_audit.dow.on(0)
    files_audit.hour.on(2)
    files_audit.minute.on(0)  # Sunday 2:00 a.m.

    glacier_inventory = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/glacier_inventory.sh')))
    glacier_inventory.dow.on(0)
    glacier_inventory.hour.on(0)
    glacier_inventory.minute.on(0)  # Sunday 12:00 a.m.

    glacier_audit = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/glacier_audit.sh')))
    glacier_audit.dow.on(0)
    glacier_audit.hour.on(6)
    glacier_audit.minute.on(0)  # Sunday 6:00 a.m.

    triggered_mails = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/triggered_mails.sh')))
    triggered_mails.hour.on(0)
    triggered_mails.minute.on(0)  # Daily 12 a.m.

    send_queued_mails = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/send_queued_mails.sh')))
    send_queued_mails.hour.on(12)
    send_queued_mails.minute.on(0)  # Daily 12 p.m.

    usage_audit = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/osfstorage/usage_audit.sh')))
    usage_audit.hour.on(0)
    usage_audit.minute.on(0)  # Daily 12 a.m.

    logger.info('Updating crontab file:')
    logger.info(cron.render())

    if not dry_run:
        cron.write_to_user(settings.CRON_USER)


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run=dry_run)
