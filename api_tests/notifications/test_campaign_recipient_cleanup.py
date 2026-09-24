from datetime import timedelta

import pytest
from django.utils import timezone

from website import settings
from osf.models import (
    NotificationCampaign,
    NotificationCampaignRecipient,
    NotificationTypeEnum,
)
from osf_tests.factories import AuthUserFactory
from notifications.tasks import delete_notification_campaign_recipients


@pytest.mark.django_db
class TestDeleteNotificationCampaignRecipients:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.notification_type = NotificationTypeEnum.BLANK.instance

    def test_deletes_recipients_for_old_campaigns(self):
        now = timezone.now()
        cutoff = now - settings.NOTIFICATION_CAMPAIGN_RECIPIENTS_CLEANUP_AGE

        campaign = NotificationCampaign.objects.create(
            name='Old campaign',
            notification_type=self.notification_type,
            completed_at=cutoff - timedelta(seconds=1),
        )

        recipients = NotificationCampaignRecipient.objects.bulk_create([
            NotificationCampaignRecipient(
                campaign=campaign,
                user_id=AuthUserFactory().id,
            ),
            NotificationCampaignRecipient(
                campaign=campaign,
                user_id=AuthUserFactory().id,
            ),
        ])

        delete_notification_campaign_recipients()

        assert not NotificationCampaignRecipient.objects.filter(
            id__in=[recipient.id for recipient in recipients],
        ).exists()

    def test_does_not_delete_recipients_for_recent_campaigns(self):
        now = timezone.now()
        cutoff = now - settings.NOTIFICATION_CAMPAIGN_RECIPIENTS_CLEANUP_AGE

        campaign = NotificationCampaign.objects.create(
            name='Recent campaign',
            notification_type=self.notification_type,
            completed_at=cutoff + timedelta(seconds=1),
        )

        recipient = NotificationCampaignRecipient.objects.create(
            campaign=campaign,
            user_id=AuthUserFactory().id,
        )

        delete_notification_campaign_recipients()

        assert NotificationCampaignRecipient.objects.filter(
            id=recipient.id,
        ).exists()

    def test_does_not_delete_recipients_for_incomplete_campaigns(self):
        campaign = NotificationCampaign.objects.create(
            name='Incomplete campaign',
            notification_type=self.notification_type,
            completed_at=None,
        )

        recipient = NotificationCampaignRecipient.objects.create(
            campaign=campaign,
            user_id=AuthUserFactory().id,
        )

        delete_notification_campaign_recipients()

        assert NotificationCampaignRecipient.objects.filter(
            id=recipient.id,
        ).exists()

    def test_deletes_recipients_in_batches(self):
        now = timezone.now()
        cutoff = now - settings.NOTIFICATION_CAMPAIGN_RECIPIENTS_CLEANUP_AGE

        campaign = NotificationCampaign.objects.create(
            name='Large campaign',
            notification_type=self.notification_type,
            completed_at=cutoff - timedelta(seconds=1),
        )

        NotificationCampaignRecipient.objects.bulk_create([
            NotificationCampaignRecipient(
                campaign=campaign,
                user_id=AuthUserFactory().id,
            )
            for _ in range(10)
        ])

        assert NotificationCampaignRecipient.objects.filter(
            campaign=campaign,
        ).count() == 10

        delete_notification_campaign_recipients()

        assert not NotificationCampaignRecipient.objects.filter(
            campaign=campaign,
        ).exists()
