from django.core.management.base import BaseCommand
from osf.models.notifications import NotificationSubscription
from osf.models import OSFUser, Node
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create duplicate notifications for testing'

    def handle(self, *args, **kwargs):
        user = OSFUser.objects.first()
        node = Node.objects.first()
        event_name = 'file_added'

        if not user or not node:
            self.stdout.write(self.style.ERROR('User or Node not found. Please ensure they exist in the database.'))
            return

        duplicate_id = f'{node._id}_{event_name}'

        for _ in range(3):
            notification = NotificationSubscription.objects.create(
                user=user,
                node=node,
                event_name=event_name,
                _id=duplicate_id,
                created=timezone.now()
            )
            notification.email_transactional.add(user)
            notification.save()

        self.stdout.write(self.style.SUCCESS('Successfully created duplicate notifications with the same _id'))
