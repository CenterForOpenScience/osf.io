import logging

from django.core.management.base import BaseCommand
from django.db.models import Count, Q


from osf.models import DraftRegistration

logger = logging.getLogger(__name__)


def retrieve_draft_registrations_to_sync():
    # Retrieve all active draft registrations
    active_draft_registrations = DraftRegistration.objects.filter(
        Q(deleted__isnull=True)
        & (Q(registered_node=None) | Q(registered_node__is_deleted=True))
    )
    # Retrieve the subset of all active draft registrations that branched from a Node
    active_draft_registrations_node = active_draft_registrations.filter(
        branched_from__type="osf.node"
    )
    # Retrieve the subset with only 1 contributor (the initiator)
    active_unsynced_draft_regs = active_draft_registrations_node.annotate(
        num_contributor=Count("_contributors")
    ).filter(num_contributor__lte=1)
    return active_unsynced_draft_regs


def project_to_draft_registration_contributor_sync(dry_run=False):
    active_unsynced_draft_regs = retrieve_draft_registrations_to_sync()
    logger.debug(
        f"A total of {active_unsynced_draft_regs.count()} draft registrations will be synced with the contributors from their projects."
    )

    for draft_reg in active_unsynced_draft_regs:
        if dry_run:
            logger.info(
                f"{draft_reg._id} will copy contributors from the {draft_reg.branched_from._id} project."
            )
            continue
        draft_reg.copy_contributors_from(draft_reg.branched_from)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry_run",
            action="store_true",
            help="Iterate through draft registrations but don't copy contributors",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        project_to_draft_registration_contributor_sync(dry_run=dry_run)
