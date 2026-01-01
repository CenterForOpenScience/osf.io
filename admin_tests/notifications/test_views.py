import pytest
from django.test import RequestFactory
from osf.models import OSFUser, Node
from admin.notifications.views import (
    delete_selected_notifications,
)
from osf.models.notification_subscription import NotificationSubscription
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db

class TestNotificationFunctions(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = OSFUser.objects.create(username='admin', is_staff=True)
        self.node = Node.objects.create(creator=self.user, title='Test Node')
        self.request_factory = RequestFactory()

    def test_delete_selected_notifications(self):
        notification1 = NotificationSubscription.objects.create(user=self.user)
        notification2 = NotificationSubscription.objects.create(user=self.user)
        notification3 = NotificationSubscription.objects.create(user=self.user)

        delete_selected_notifications([notification1.id, notification2.id])

        assert not NotificationSubscription.objects.filter(id__in=[notification1.id, notification2.id]).exists()
        assert NotificationSubscription.objects.filter(id=notification3.id).exists()
