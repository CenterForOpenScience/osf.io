import pytest
from django.test import RequestFactory
from osf.models import OSFUser, Node
from admin.notifications.views import (
    delete_selected_notifications,
    detect_duplicate_notifications,
)
from osf.models.notifications import NotificationSubscriptionLegacy
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db

class TestNotificationFunctions(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = OSFUser.objects.create(username='admin', is_staff=True)
        self.node = Node.objects.create(creator=self.user, title='Test Node')
        self.request_factory = RequestFactory()

    def test_delete_selected_notifications(self):
        notification1 = NotificationSubscriptionLegacy.objects.create(user=self.user, node=self.node, event_name='event1')
        notification2 = NotificationSubscriptionLegacy.objects.create(user=self.user, node=self.node, event_name='event2')
        notification3 = NotificationSubscriptionLegacy.objects.create(user=self.user, node=self.node, event_name='event3')

        delete_selected_notifications([notification1.id, notification2.id])

        assert not NotificationSubscriptionLegacy.objects.filter(id__in=[notification1.id, notification2.id]).exists()
        assert NotificationSubscriptionLegacy.objects.filter(id=notification3.id).exists()

    def test_detect_duplicate_notifications(self):
        NotificationSubscriptionLegacy.objects.create(user=self.user, node=self.node, event_name='event1')
        NotificationSubscriptionLegacy.objects.create(user=self.user, node=self.node, event_name='event1')
        NotificationSubscriptionLegacy.objects.create(user=self.user, node=self.node, event_name='event2')

        duplicates = detect_duplicate_notifications()

        print(f"Detected duplicates: {duplicates}")

        assert len(duplicates) == 3, f"Expected 3 duplicates, but found {len(duplicates)}"
