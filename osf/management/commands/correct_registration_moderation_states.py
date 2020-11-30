import logging

from django.core.management.base import BaseCommand
from osf.models import Registration
from osf.utils.workflows import RegistrationModerationStates

logger = logging.getLogger(__name__)

def correct_registration_moderation_states():
    '''Backfill the moderation_state field of all registrations based on its current Sanction.'''

    # Any registration with a non-INITIAL state is already subject to the new
    # sanction state machine flows and should have the correct moderation_state
    default_value = RegistrationModerationStates.INITIAL.db_name
    out_of_date_registrations = Registration.objects.filter(
        deleted__isnull=True, moderation_state=default_value)

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

    def handle(self, *args, **options):
        correct_registration_moderation_states()
