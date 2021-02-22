import logging

from django.core.management.base import BaseCommand

from framework.celery_tasks import app as celery_app
from osf.models import Registration
from osf.utils.workflows import RegistrationModerationStates

logger = logging.getLogger(__name__)


@celery_app.task(name='management.commands.correct_registration_moderation_states')
def correct_registration_moderation_states(page_size=None):
    '''Backfill the moderation_state field of all registrations based on its current Sanction.'''

    # Any registration with a non-INITIAL state is already subject to the new
    # sanction state machine flows and should have the correct moderation_state
    # Unapproved RegistrationApprovals and Embargoes should have an INITIAL state,
    # and are excluded.
    default_value = RegistrationModerationStates.INITIAL.db_name
    out_of_date_registrations = Registration.objects.filter(
        deleted__isnull=True, moderation_state=default_value
    ).exclude(
        registration_approval__state='unapproved'
    ).exclude(embargo__state='unapproved')

    if page_size:
        out_of_date_registrations = out_of_date_registrations[:page_size]

    corrected_registration_count = 0
    for registration in out_of_date_registrations:
        registration.update_moderation_state()
        if registration.moderation_state != default_value:
            logger.info(
                f'Corrected moderation_state value for Registration with ID {registration._id}. '
                f'New value is {registration.moderation_state}'
            )
            corrected_registration_count += 1

    logger.info(f'Corrected the moderation_state for {corrected_registration_count} Registrations')
    return corrected_registration_count


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--page_size',
            type=int,
            default=0,
            help='How many rows to process at a time. 0 indicates "all"',
        )

    def handle(self, *args, **options):
        page_size = options.get('page_size', 0)
        correct_registration_moderation_states(page_size)
