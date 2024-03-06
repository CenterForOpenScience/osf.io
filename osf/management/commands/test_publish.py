from django.core.management.base import BaseCommand
from osf.models import OSFUser
from osf.external.messages.celery_publishers import (
    publish_deactivated_user,
    publish_reactivate_user,
    publish_merged_user,
)


class Command(BaseCommand):
    help = 'Sends a message to manage a user state, for test purposes only.'

    def add_arguments(self, parser):
        parser.add_argument('user_guid', type=str, help='URI of the user to post.')
        # Adding a new argument to specify the action to perform
        parser.add_argument(
            'action',
            type=str,
            help='The action to perform on the user (deactivate, reactivate, merge).',
            choices=['deactivate', 'reactivate', 'merge']  # Limiting the choices to specific actions
        )

    def handle(self, *args, **options):
        user_guid = options['user_guid']
        user = OSFUser.objects.get(guids___id=user_guid)
        action = options['action']

        # Using a mapping of action to function to simplify the control flow
        actions_to_functions = {
            'deactivate': publish_deactivated_user,
            'reactivate': publish_reactivate_user,
            'merge': publish_merged_user,
        }

        if action in actions_to_functions:
            actions_to_functions[action](user)  # Call the appropriate function
            self.stdout.write(self.style.SUCCESS(f'Successfully {action} message for user: {user._id}'))
        else:
            self.stdout.write(self.style.ERROR('Invalid action specified.'))
