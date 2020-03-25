import logging
import sys

from website.app import setup_django
setup_django()

import pytz
import argparse
from django.db import transaction
import datetime
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from scripts import utils as scripts_utils
from osf.models import DraftRegistration
from django.core.paginator import Paginator
from osf.models import DraftRegistrationContributor
from tqdm import tqdm



def main(dry=True, page_size=1000):
    """
    for 0199_draft_node_permissions we had a bug where permissions groups were made, but not actually populated leading
    to a widespread permissions errors for draft registrations made prior to the migration. This should fix that.
    Migration ran at 2120 (EDT).
    """
    date_of_migration = datetime.datetime(2020, 3, 24, 1, 20, tzinfo=pytz.utc)

    bugged_regs = DraftRegistration.objects.filter(
        created__lte=date_of_migration
    ).exclude(
        _contributors__isnull=False
    )

    paginator = Paginator(bugged_regs, page_size)
    for page_num in tqdm(paginator.page_range, desc='Page of migration'):
        page = paginator.page(page_num)
        with transaction.atomic():
            for reg in tqdm(page, desc='Progress'):
                draft_perm_groups = reg.group_objects.order_by('name')
                node_perm_groups = reg.branched_from.group_objects.order_by('name')

                for draft_perm_group, node_perm_group in zip(draft_perm_groups, node_perm_groups):
                    node_users = node_perm_group.user_set.all()
                    if dry:
                        logger.info(f'{draft_perm_group} updated from {node_perm_group}')
                        continue
                    draft_perm_group.user_set.add(*node_users)

                for contrib in reg.branched_from.contributor_set.all():
                    if dry:
                        logger.info(f'{contrib._id} added')
                        continue

                    DraftRegistrationContributor(
                        draft_registration=reg,
                        _order=contrib._order,
                        visible=contrib.visible,
                        user=contrib.user
                    ).save()


if __name__ == '__main__':

    cli = argparse.ArgumentParser()
    cli.add_argument(
        '--page_size',
        type=int,
        default=1000,
        help='How many items at a time to include for each query',
    )
    cli.add_argument(
        '--dry',
        action='store_true',
    )
    args = cli.parse_args()

    if not args.dry:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry=args.dry, page_size=args.page_size)
