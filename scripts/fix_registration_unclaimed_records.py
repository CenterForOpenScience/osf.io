import logging
import sys

from django.db import transaction

from framework.auth.core import generate_verification_key
from website.app import setup_django
setup_django()
from osf.models import Registration, OSFUser
from scripts import utils as script_utils


logger = logging.getLogger(__name__)

def main():
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        qs = Registration.objects.filter(_contributors__is_registered=False, is_deleted=False)
        logger.info('Found {} registrations with unregistered contributors'.format(qs.count()))
        for registration in qs:
            registration_id = registration._id
            logger.info('Adding unclaimed_records for unregistered contributors on {}'.format(registration_id))
            registered_from_id = registration.registered_from._id

            # Update unclaimed records for all unregistered contributors in the registration
            for contributor in registration.contributors.filter(is_registered=False):
                contrib_id = contributor._id

                # Most unregistered users will have a record for the registration's node
                record = contributor.unclaimed_records.get(registered_from_id)

                if not record:
                    # Old unregistered contributors that have been removed from the original node will not have a record
                    logger.info('No record for node {} for user {}, inferring from other data'.format(registered_from_id, contrib_id))

                    # Get referrer id from logs
                    for log in registration.logs.filter(action='contributor_added').order_by('date'):
                        if contrib_id in log.params['contributors']:
                            referrer_id = str(OSFUser.objects.get(id=log.user_id)._id)
                            break
                    else:
                        # This should not get hit. Worst outcome is that resent claim emails will fail to send via admin for this record
                        logger.info('No record of {} in {}\'s logs.'.format(contrib_id, registration_id))
                        referrer_id = None

                    verification_key = generate_verification_key(verification_type='claim')

                    # name defaults back to name given in first unclaimed record
                    record = {
                        'name': contributor.given_name,
                        'referrer_id': referrer_id,
                        'token': verification_key['token'],
                        'expires': verification_key['expires'],
                        'email': None,
                    }

                logger.info('Writing new unclaimed_record entry for user {} for registration {}.'.format(contrib_id, registration_id))
                contributor.unclaimed_records[registration_id] = record
                contributor.save()

        if dry:
            raise Exception('Abort Transaction - Dry Run')
    print('Done')

if __name__ == '__main__':
    main()
