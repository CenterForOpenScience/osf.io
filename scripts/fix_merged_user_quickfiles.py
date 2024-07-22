import logging
import sys

from django.db import transaction
from django.db.models import F, Count

from website.app import setup_django
setup_django()
from osf.models import QuickFilesNode
from scripts import utils as script_utils


logger = logging.getLogger(__name__)

def main():
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        qs = QuickFilesNode.objects.exclude(_contributors=F('creator')).annotate(contrib_count=Count('_contributors')).exclude(contrib_count=0)
        logger.info(f'Found {qs.count()} quickfiles nodes with mismatched creator and _contributors')

        for node in qs:
            bad_contrib = node._contributors.get()
            logger.info(f'Fixing {node._id} (quickfiles node): Replacing {bad_contrib._id} (bad contributor) with {node.creator._id} (creator)')
            node.contributor_set.filter(user=bad_contrib).update(user=node.creator)
            node.save()
        if dry:
            raise Exception('Abort Transaction - Dry Run')
    print('Done')

if __name__ == '__main__':
    main()
