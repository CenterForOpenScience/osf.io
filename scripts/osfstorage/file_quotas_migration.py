import logging
from website import mails
from website.app import init_app
from framework.auth.core import User
from website.project.model import Node
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)


LEEWAY_SPACE = (1024 ** 3)  # 1.0 GB
WARNING_EMAIL_CUT_OFF = (1024 ** 3) * 1.5  # 1.5 GB


def migrate_users(send_emails=False):
    for user in User.find():
        addon = user.get_addon('osfstorage')
        addon.calculate_storage_usage(save=True)

        if addon.storage_usage >= WARNING_EMAIL_CUT_OFF:
            addon.storage_limit_override = addon.storage_usage + LEEWAY_SPACE
            logger.warning('User {} is using {} bytes (>=1.5GB) of storage. Sending warning email.'.format(user, addon.storage_usage))
            addon.save()
            if send_emails:
                mails.send_mail(addon.owner, mails.OSFSTORAGE_MIGRATION_WARNING, fullname=addon.owner.fullname)
        else:
            logger.info('User {} is using {} bytes of storage.'.format(user, addon.storage_usage))


def migrate_nodes():
    for node in Node.find():
        addon = node.get_addon('osfstorage')
        addon.calculate_storage_usage(save=True)
        logger.info('Node {} is using {} bytes of storage.'.format(node, addon.storage_usage))


def main(dry=True):
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate_users(send_emails=not dry)
        migrate_nodes()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    import sys

    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)

    main(dry='dry' in sys.argv)
