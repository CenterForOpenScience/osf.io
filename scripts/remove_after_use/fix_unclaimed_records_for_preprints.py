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
                logger.info(u'User {} has been given an unclaimed record with name {} for node {}'.format(user._id, user.fullname, node._id))
            else:
                logger.info('User {} has could not be given a record, because their referer was anonymous'.format(user._id))


def main(dry_run=True):
    users = OSFUser.objects.filter(date_disabled__isnull=True,
                                   is_registered=False,
                                   unclaimed_records={},
                                   nodes__is_deleted=False,
                                   nodes__type='osf.node').include(None).distinct()
    logger.info('{} users without unclaimed records'.format(users.count()))
    for user in users:
        for node in user.nodes.filter(type='osf.node'):
            if user.unclaimed_records.get(node._id) is None:
                add_missing_unclaimed_record(user, node, dry_run)


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    if not dry_run:
        utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
