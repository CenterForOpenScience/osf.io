import pytest
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from osf.models import NotificationType, NotificationSubscription, OSFUser
from osf.admin import (
    NotificationTypeAdmin,
    NotificationSubscriptionAdmin,
    NotificationTypeAdminForm,
    NotificationSubscriptionForm
)
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db


class TestNotificationAdminAppSection(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = OSFUser.objects.create(username='admin', is_staff=True)
        self.notification_type = NotificationType.objects.create(
            name='Test Notification',
            subject='Hello',
            template='Sample Template',
            notification_interval_choices=['daily', 'custom']
        )
        self.subscription = NotificationSubscription.objects.create(
            user=self.user,
            notification_type=self.notification_type,
            message_frequency='daily',
            subscribed_object=None
        )
        self.admin_site = AdminSite()
        self.request_factory = RequestFactory()

    def test_notification_type_admin_preview_button(self):
        admin = NotificationTypeAdmin(NotificationType, self.admin_site)
        html = admin.preview_button(self.notification_type)
        assert f'{self.notification_type.id}/preview/' in html
        assert 'Preview' in html

    def test_notification_type_admin_preview_view(self):
        admin = NotificationTypeAdmin(NotificationType, self.admin_site)
        request = self.request_factory.get(f'/admin/osf/notificationtype/{self.notification_type.id}/preview/')
        request.user = self.user
        response = admin._preview_notification_template_view(request, pk=self.notification_type.id)
        content = response.content.decode()

        assert response.status_code == 200
        assert 'Template Preview for' in content
        assert self.notification_type.name in content
        assert self.notification_type.subject in content

    def test_notification_type_admin_form_save_combines_intervals(self):
        form_data = {
            'name': 'Updated Notification',
            'subject': 'Updated Subject',
            'template': 'Updated Template',
            'default_intervals': ['daily'],
            'custom_intervals': ['weekly']
        }
        form = NotificationTypeAdminForm(data=form_data, instance=self.notification_type)
        assert form.is_valid(), form.errors
        instance = form.save()
        assert set(instance.notification_interval_choices) == {'daily', 'weekly'}

    def test_notification_subscription_admin_preview_button(self):
        admin = NotificationSubscriptionAdmin(NotificationSubscription, self.admin_site)
        html = admin.preview_button(self.subscription)
        assert f'/admin/osf/notificationtype/{self.notification_type.id}/preview/' in html
        assert 'Preview' in html

    def test_notification_subscription_admin_get_intervals(self):
        admin = NotificationSubscriptionAdmin(NotificationSubscription, self.admin_site)
        request = self.request_factory.get(f'/admin/osf/notificationsubscription/get-intervals/{self.notification_type.id}/')
        request.user = self.user
        response = admin.get_intervals(request, pk=self.notification_type.id)
        assert response.status_code == 200

    def test_notification_subscription_form_sets_choices(self):
        form = NotificationSubscriptionForm(data={'notification_type': self.notification_type.id})
        assert 'message_frequency' in form.fields
        expected_choices = [(x, x) for x in self.notification_type.notification_interval_choices]
        assert form.fields['message_frequency'].choices == expected_choices
