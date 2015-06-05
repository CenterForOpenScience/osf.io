# -*- coding: utf-8 -*-

import os
import sys
import logging

import crontab

from website import settings

import tasks


N_AUDIT_WORKERS = 4

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def app_prefix(path):
    return os.path.join(settings.APP_PATH, path)


def cd_app(command):
    return 'cd {0} && {1}'.format(settings.APP_PATH, command)


def run_python_script(command):
    return cd_app(app_prefix(command))


def ensure_item(cron, command):
    items = list(cron.find_command(command))
    return items[0] if items else cron.new(command)


def schedule_osf_storage(cron):
    for idx in range(N_AUDIT_WORKERS):
        audit = ensure_item(
            cron,
            cd_app(
                tasks.bin_prefix(
                    'python -m scripts.osfstorage.files_audit {0} {1}'.format(
                        N_AUDIT_WORKERS,
                        idx,
                    )
                )
            )
        )
        audit.dow.on(0)     # Sunday
        audit.hour.on(2)    # 2 a.m.


def schedule_glacier(cron):
    glacier_inventory = ensure_item(
        cron,
        cd_app(
            tasks.bin_prefix(
                'python -m scripts.osfstorage.glacier_inventory'
            )
        )
    )
    glacier_inventory.dow.on(0)     # Sunday
    glacier_inventory.hour.on(0)    # 12 a.m.

    glacier_audit = ensure_item(
        cron,
        run_python_script(
            'python -m scripts.osfstorage.glacier_audit'
        )
    )
    glacier_audit.dow.on(0)         # Sunday
    glacier_audit.hour.on(6)        # 6 a.m.


def main(dry_run=True):

    cron = crontab.CronTab(user=settings.CRON_USER)

    analytics = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/analytics.sh')))
    analytics.hour.on(2)    # 2 a.m.

    digests = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/send_digests.sh')))
    digests.hour.on(2)      # 2 a.m.

    retractions = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/retract_registrations.sh')))
    retractions.hour.on(0)  # 12 a.m.

    embargoes = ensure_item(cron, 'bash {}'.format(app_prefix('scripts/embargo_registrations.sh')))
    embargoes.hours.on(0)   # 12 a.m.

    schedule_osf_storage(cron)
    schedule_glacier(cron)

    logger.info('Updating crontab file:')
    logger.info(cron.render())

    if not dry_run:
        cron.write_to_user(settings.CRON_USER)


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run=dry_run)
