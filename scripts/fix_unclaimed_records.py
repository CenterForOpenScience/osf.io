import sys
import logging
from website.app import setup_django

setup_django()
from osf.models import OSFUser
logger = logging.getLogger(__name__)


def add_missing_unclaimed_record(user, node, dry_run):
    # Get referrer from logs
    for log in node.logs.filter(action='contributor_added').order_by('date'):
        if user._id in log.params['contributors']:
            if log.user_id:
                referrer = OSFUser.objects.get(id=log.user_id)
                user.add_unclaimed_record(node, referrer, user.fullname)
                if not dry_run:
                    user.save()
                logger.info('User {} has been given an unclaimed record with name {} for node {}'.format(user._id, user.fullname, node._id))
            else:
                logger.info('User {} has could not be given a record, because their referer was anonymous'.format(user._id))


def main(dry_run=True):
    users = OSFUser.objects.filter(is_registered=False).filter(nodes__type='osf.node').include(None).distinct()
    logger.info('{} users without unclaimed records'.format(users.count()))
    for user in users:
        for node in user.nodes.filter(type='osf.node'):
            if user.unclaimed_records.get(node._id) is None:
                add_missing_unclaimed_record(user, node, dry_run)


if __name__ == "__main__":
    main(dry_run='--dry' in sys.argv)
