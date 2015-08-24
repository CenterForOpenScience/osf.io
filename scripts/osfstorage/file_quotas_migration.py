import logging
from modularodm import Q
from website import mails
from website.app import init_app
from framework.auth.core import User
from website.project.model import Node
from scripts import utils as scripts_utils
from website.addons.osfstorage import model
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)


LEEWAY_SPACE = (1024 ** 3)  # 1.0 GB
WARNING_EMAIL_CUT_OFF = (1024 ** 3) * 1.5  # 1.5 GB


def migrate_deleted():
    logger.info('Migrating OsfStorageTrashedFileNodes')
    for file_node in model.OsfStorageTrashedFileNode.find():
        for version in file_node.versions:
            version.deleted = True
            version.save()


def migrate_registrations():
    logger.info('Migrating registrations')
    for node in Node.find(Q('is_registration', 'eq', True)):
        logger.debug('Migrating registration {}'.format(node))
        for file_node in model.OsfStorageFileNode.find(Q('node_settings', 'eq', node.get_addon('osfstorage'))):
            for version in file_node.versions:
                version.delete = False
                version.ignore_size = True
                version.save()


def migrate_nodes():
    logger.info('Migrating non-registrations')
    for node in Node.find(Q('is_registration', 'eq', False)):
        logger.debug('Migrating node {}'.format(node))
        addon = node.get_addon('osfstorage')
        for file_node in model.OsfStorageFileNode.find(Q('node_settings', 'eq', addon)):
            for version in file_node.versions:
                version._find_duplicates(save=True)
                if version.deleted:
                    logger.warning('Version {} was incorrectly marked as deleted.'.format(version._id))
                    version.deleted = False
                    version.save()
                if version.ignore_size:
                    logger.info('Version {} is part of a registration, keeping ignore_size.'.format(version._id))

        addon.calculate_storage_usage(save=True)
        logger.info('Node {} is using {} bytes of storage.'.format(node, addon.storage_usage))


def migrate_users(send_emails=False):
    logger.info('Migrating users')
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


def main(dry=True, send_emails=False):
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate_deleted()
        migrate_registrations()
        migrate_nodes()
        migrate_users(send_emails=send_emails)
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

    if 'dry' not in sys.argv:
        scripts_utils.add_file_logger(logger, __file__)

    main(dry='dry' in sys.argv, send_emails='send_emails' in sys.argv)
