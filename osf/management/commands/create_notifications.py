from django.core.management.base import BaseCommand
from osf.models.notifications import NotificationSubscription
from osf.models import OSFUser, Node
from django.utils.crypto import get_random_string
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create duplicate notifications for testing'

    def handle(self, *args, **kwargs):
        user = OSFUser.objects.first()
        node = Node.objects.first()
        event_name = 'file_added'

        for _ in range(3):
            unique_id = get_random_string(length=32)
            notification = NotificationSubscription.objects.create(
                user=user,
                node=node,
                event_name=event_name,
                _id=unique_id,
                created=timezone.now()
            )
            notification.email_transactional.add(user)
            notification.save()

        self.stdout.write(self.style.SUCCESS('Successfully created duplicate notifications'))