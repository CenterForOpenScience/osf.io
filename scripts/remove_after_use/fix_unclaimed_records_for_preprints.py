import sys
import logging

from framework.auth.core import generate_verification_key
from website.app import setup_django

setup_django()
from osf.models import OSFUser
from scripts import utils

logger = logging.getLogger(__name__)


def add_missing_unclaimed_record(user, node, dry_run):
    # Get referrer from logs
    for log in node.logs.filter(action='contributor_added').order_by('date'):
        if user._id in log.params['contributors']:
            if log.user_id:
                referrer = OSFUser.objects.get(id=log.user_id)
                verification_key = generate_verification_key(verification_type='confirm')
                record = {
                    'name': user.fullname,
                    'referrer_id': referrer._id,
                    'token': verification_key['token'],
                    'expires': verification_key['expires'],
                    'email': None,
                }
                user.unclaimed_records[node._id] = record

                if not dry_run:
                    user.save()
                logger.info(
                    u'User {} has been given an unclaimed record with name {} for node {}{}'.format(
                        user._id,
                        user.fullname,
                        node._id,
                        ' (PUBLIC)' if node.is_public else ''
                    )
                )
            else:
                logger.info('User {} could not be given a record, because their referrer was anonymous'.format(user._id))


def main(dry_run=True):
    count = 0
    users = OSFUser.objects.filter(date_disabled__isnull=True,
                                   is_registered=False,
                                   nodes__is_deleted=False,
                                   nodes__type='osf.node').include(None).distinct()
    logger.info('Checking {} unregistered users'.format(users.count()))
    for user in users:
        for node in user.nodes.exclude(type='osf.quickfilesnode').exclude(is_deleted=True):
            if user.unclaimed_records.get(node._id) is None:
                count += 1
                add_missing_unclaimed_record(user, node, dry_run)
    logger.info('Added {} unclaimed records'.format(count))


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    if not dry_run:
        utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
