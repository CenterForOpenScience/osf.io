import logging
import sys

from website.app import setup_django
setup_django()

import pytz
from django.db import transaction
from osf.models import EmbargoTerminationApproval
from osf.models import Sanction
import datetime
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from scripts import utils as scripts_utils

from osf.models import DraftRegistration


def main(dry=True):
    """
    for 0199_draft_node_permissions we had a bug where permissions groups were made, but not actually populated leading
    to a widespread permissions errors for draft registrations made prior to the migration. This should fix that.
    Migration ran at 2120 (EDT).
    """
    date_of_migration = datetime.datetime(2020, 3, 24, 21, 20, tzinfo=pytz.utc)

    bugged_regs = DraftRegistration.objects.filter(created__lte=date_of_migration)

    with transaction.atomic():
        for reg in bugged_regs:
            draft_perm_groups = reg.group_objects.order_by('name')
            node_perm_groups = reg.branched_from.group_objects.order_by('name')

            for draft_perm_group, node_perm_group in zip(draft_perm_groups, node_perm_groups):
                node_users = node_perm_group.user_set.all()
                if dry:
                    logger.info(f'{draft_perm_group} updated from {node_perm_group}')
                    continue
                draft_perm_group.user_set.add(*node_users)



if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry=dry)
