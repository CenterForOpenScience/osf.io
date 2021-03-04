import logging

from django.core.management.base import BaseCommand
from django.db.models import Count, Q


from osf.models import DraftRegistration

logger = logging.getLogger(__name__)


def project_to_draft_registration_contributor_sync():
    # Retrieve all active draft registrations
    active_draft_registrations = DraftRegistration.objects.filter(Q(deleted__isnull=True) & (Q(registered_node=None) | Q(registered_node__is_deleted=True)))
    # Retrieve active draft registrations with only 1 contributor (the initiator)
    active_unsynced_draft_regs = active_draft_registrations.annotate(num_contributor=Count('_contributors')).filter(num_contributor=1)
    logger.debug(f'A total of {active_unsynced_draft_regs.count()} draft registrations will be synced with the contributors from their projects.')

    for draft_reg in active_unsynced_draft_regs:
        draft_reg.copy_contributors_from(draft_reg.branched_from)


class Command(BaseCommand):

    def handle(self, *args, **options):
        project_to_draft_registration_contributor_sync()
