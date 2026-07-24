import pytest
from datetime import timedelta

from django.utils import timezone

from osf.email.notification_campaign import (
    create_campaign_recipients,
    get_campaign_recipient_batches,
)
from osf.models import NotificationType, UserActivityCounter
from osf.models.notification_campaign import (
    NotificationCampaign,
    NotificationCampaignRecipient,
)
from osf.models.spam import SpamStatus
from osf_tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def notification_type():
    notification_type, _ = NotificationType.objects.get_or_create(name='blank')
    return notification_type


@pytest.fixture
def campaign(notification_type):
    return NotificationCampaign.objects.create(
        name='Test campaign',
        notification_type=notification_type,
        metadata={'execution': {'activity_threshold': 100, 'batch_size': 2}},
    )


def _set_activity(user, total):
    UserActivityCounter.objects.update_or_create(
        _id=user._id,
        defaults={'total': total, 'action': {}, 'date': {}},
    )


def _recipient_user_ids(campaign_id, **batch_kwargs):
    """Flatten all batches into an list of user ids and preserve order"""
    user_ids = []
    for batch in get_campaign_recipient_batches(campaign_id=campaign_id, batch_size=1000, **batch_kwargs):
        recipients = NotificationCampaignRecipient.objects.filter(id__in=batch)
        by_id = {r.id: r.user_id for r in recipients}
        user_ids.extend(by_id[recipient_id] for recipient_id in batch)
    return user_ids


def _recipient_scores(campaign_id, **batch_kwargs):
    """Flatten all batches into an list of activity scores and preserve order"""
    scores = []
    for batch in get_campaign_recipient_batches(campaign_id=campaign_id, batch_size=1000, **batch_kwargs):
        by_id = {
            r.id: r.activity_score
            for r in NotificationCampaignRecipient.objects.filter(id__in=batch)
        }
        scores.extend(by_id[recipient_id] for recipient_id in batch)
    return scores


class TestCreateCampaignRecipients:

    def test_creates_recipients_with_activity_scores(self, campaign):
        high = UserFactory()
        low = UserFactory()
        zero = UserFactory()
        _set_activity(high, 500)
        _set_activity(low, 50)

        create_campaign_recipients(
            filters={'id__in': [high.id, low.id, zero.id]},
            campaign_id=campaign.id,
        )

        recipients = {
            r.user_id: r.activity_score
            for r in NotificationCampaignRecipient.objects.filter(campaign=campaign)
        }
        assert recipients[high.id] == 500
        assert recipients[low.id] == 50
        assert recipients[zero.id] == 0
        assert NotificationCampaignRecipient.objects.filter(campaign=campaign).count() == 3

    def test_respects_user_filters(self, campaign):
        included = UserFactory(is_staff=True)
        excluded = UserFactory(is_staff=False)
        _set_activity(included, 10)
        _set_activity(excluded, 10)

        create_campaign_recipients(
            filters={'id__in': [included.id, excluded.id], 'is_staff': True},
            campaign_id=campaign.id,
        )

        user_ids = set(
            NotificationCampaignRecipient.objects.filter(campaign=campaign).values_list('user_id', flat=True)
        )
        assert user_ids == {included.id}

    def test_ordered_by_activity_score_descending(self, campaign):
        older = UserFactory()
        newer = UserFactory()
        mid = UserFactory()
        older.date_registered = timezone.now() - timedelta(days=3)
        mid.date_registered = timezone.now() - timedelta(days=2)
        newer.date_registered = timezone.now() - timedelta(days=1)
        older.save(update_fields=['date_registered'])
        mid.save(update_fields=['date_registered'])
        newer.save(update_fields=['date_registered'])

        _set_activity(older, 10)
        _set_activity(mid, 50)
        _set_activity(newer, 50)

        create_campaign_recipients(
            filters={'id__in': [older.id, newer.id, mid.id]},
            campaign_id=campaign.id,
        )

        scores = _recipient_scores(campaign.id)
        assert scores == sorted(scores, reverse=True)
        user_ids = _recipient_user_ids(campaign.id)
        assert user_ids == [mid.id, newer.id, older.id]


class TestGetCampaignRecipientBatches:

    @pytest.fixture
    def users_and_recipients(self, campaign):
        threshold = 100
        high = UserFactory()
        low = UserFactory()
        zero = UserFactory()
        flagged = UserFactory()
        spam = UserFactory()
        spam.spam_status = SpamStatus.SPAM
        spam.save()
        flagged.spam_status = SpamStatus.FLAGGED
        flagged.save()

        _set_activity(high, 250)
        _set_activity(low, 40)
        _set_activity(flagged, 300)
        _set_activity(spam, 900)

        create_campaign_recipients(
            filters={'id__in': [high.id, low.id, zero.id, flagged.id, spam.id]},
            campaign_id=campaign.id,
        )
        return {
            'threshold': threshold,
            'high': high,
            'low': low,
            'zero': zero,
            'flagged': flagged,
            'spam': spam,
        }

    def test_high_activity_non_spam(self, campaign, users_and_recipients):
        data = users_and_recipients
        user_ids = _recipient_user_ids(
            campaign.id,
            min_activity=data['threshold'],
            spam=False,
        )
        assert set(user_ids) == {data['high'].id, data['flagged'].id}

    def test_low_activity_non_spam_includes_zero(self, campaign, users_and_recipients):
        data = users_and_recipients
        user_ids = _recipient_user_ids(
            campaign.id,
            max_activity=data['threshold'],
            spam=False,
        )
        assert set(user_ids) == {data['low'].id, data['zero'].id}

    def test_spam_only(self, campaign, users_and_recipients):
        data = users_and_recipients
        user_ids = _recipient_user_ids(campaign.id, spam=True)
        assert user_ids == [data['spam'].id]

    def test_phases_cover_all_pending_recipients(self, campaign, users_and_recipients):
        data = users_and_recipients
        threshold = data['threshold']
        all_ids = (
            set(_recipient_user_ids(campaign.id, min_activity=threshold, spam=False))
            | set(_recipient_user_ids(campaign.id, max_activity=threshold, spam=False))
            | set(_recipient_user_ids(campaign.id, spam=True))
        )
        expected = {data['high'].id, data['low'].id, data['zero'].id, data['flagged'].id, data['spam'].id}
        assert all_ids == expected

    def test_batches_respect_batch_size(self, campaign):
        users = [UserFactory() for _ in range(5)]
        for i, user in enumerate(users):
            _set_activity(user, (i + 1) * 10)

        create_campaign_recipients(
            filters={'id__in': [u.id for u in users]},
            campaign_id=campaign.id,
        )

        batches = list(get_campaign_recipient_batches(campaign_id=campaign.id, batch_size=2))
        assert [len(batch) for batch in batches] == [2, 2, 1]
        flat = {recipient_id for batch in batches for recipient_id in batch}
        assert len(flat) == 5
