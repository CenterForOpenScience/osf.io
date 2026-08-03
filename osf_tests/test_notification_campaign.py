import pytest
import uuid
from datetime import timedelta
from unittest import mock

from django.utils import timezone
from django.db.models import Q

from osf.email.notification_campaign import (
    create_campaign_recipients,
    get_campaign_recipient_batches,
    get_campaign_recipient_stats,
    process_campaign_retry,
    send_campaign_batch,
    start_notification_campaign,
    build_query,
)
from osf.models import UserActivityCounter, OSFUser
from osf.models.notification_campaign import (
    NotificationCampaign,
    NotificationCampaignRecipient,
    NotificationCampaignRecipientStatus,
    NotificationCampaignStatus,
)
from osf.models.notification_type import NotificationType
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
        metadata={
            'filters': {'manual': {'operator': 'AND', 'children': []}},
            'context': {},
            'execution': {
                'activity_threshold': 100,
                'batch_size': 2,
                'max_retries': 2,
            },
        },
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


class TestBuildQuery:

    def test_not_contains_excludes_matching_usernames(self):
        email_user = UserFactory(username='user@example.com')
        plain_user = UserFactory()
        plain_user.username = 'deleted user'
        plain_user.save(update_fields=['username'])

        query = build_query({
            'field': 'username',
            'lookup': 'not_contains',
            'value': '@',
        })
        user_ids = set(OSFUser.objects.filter(query).values_list('id', flat=True))

        assert plain_user.id in user_ids
        assert email_user.id not in user_ids

    def test_regex_matches_usernames_without_at(self):
        email_user = UserFactory(username='user@example.com')
        plain_user = UserFactory()
        plain_user.username = 'gdpr-deleted-id'
        plain_user.save(update_fields=['username'])

        query = build_query({
            'field': 'username',
            'lookup': 'regex',
            'value': r'^[^@]+$',
        })
        user_ids = set(OSFUser.objects.filter(query).values_list('id', flat=True))

        assert plain_user.id in user_ids
        assert email_user.id not in user_ids

    def test_or_combines_usernames(self):
        staging_user = UserFactory(username='tester@staging.example')
        plain_user = UserFactory()
        plain_user.username = 'uuid-style-name'
        plain_user.save(update_fields=['username'])
        other_email = UserFactory(username='other@elsewhere.example')

        query = build_query({
            'operator': 'OR',
            'children': [
                {'field': 'username', 'lookup': 'endswith', 'value': '@staging.example'},
                {'field': 'username', 'lookup': 'not_contains', 'value': '@'},
            ],
        })
        user_ids = set(OSFUser.objects.filter(query).values_list('id', flat=True))

        assert staging_user.id in user_ids
        assert plain_user.id in user_ids
        assert other_email.id not in user_ids


class TestCreateCampaignRecipients:

    def test_creates_recipients_with_activity_scores(self, campaign):
        high = UserFactory()
        low = UserFactory()
        zero = UserFactory()
        _set_activity(high, 500)
        _set_activity(low, 50)

        create_campaign_recipients(
            Q(**{'id__in': [high.id, low.id, zero.id]}),
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
            build_query({'operator': 'AND', 'children': [{'field': 'id', 'lookup': 'in', 'value': f'{included.id}, {excluded.id}'}, {'field': 'is_staff', 'lookup': 'exact', 'value': True}]}),
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
            Q(**{'id__in': [older.id, newer.id, mid.id]}),
            campaign_id=campaign.id,
        )

        scores = _recipient_scores(campaign.id)
        assert scores == sorted(scores, reverse=True)
        user_ids = _recipient_user_ids(campaign.id)
        assert user_ids == [newer.id, mid.id, older.id]


class TestGetCampaignRecipientStats:

    def test_empty_campaign(self, campaign):
        assert get_campaign_recipient_stats(campaign.id) == {
            'recipient_count': 0,
            'sent_count': 0,
            'failed_count': 0,
        }

    def test_counts_sent_failed_and_skipped(self, campaign, notification_type):
        sent = UserFactory()
        failed = UserFactory()
        skipped = UserFactory()
        pending = UserFactory()
        create_campaign_recipients(
            Q(**{'id__in': [sent.id, failed.id, skipped.id, pending.id]}),
            campaign_id=campaign.id,
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=sent).update(
            status=NotificationCampaignRecipientStatus.SENT
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=failed).update(
            status=NotificationCampaignRecipientStatus.FAILED
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=skipped).update(
            status=NotificationCampaignRecipientStatus.SKIPPED
        )

        assert get_campaign_recipient_stats(campaign.id) == {
            'recipient_count': 4,
            'sent_count': 1,
            'failed_count': 2,  # FAILED + SKIPPED
        }

    def test_scopes_to_requested_campaign(self, campaign, notification_type):
        other = NotificationCampaign.objects.create(
            name='Other campaign',
            notification_type=notification_type,
            metadata={'filters': {}, 'context': {}, 'execution': {}},
        )
        user = UserFactory()
        other_user = UserFactory()
        create_campaign_recipients(build_query({'operator': 'AND', 'children': [{'field': 'id', 'lookup': 'in', 'value': f'{user.id}'}]}), campaign_id=campaign.id)
        create_campaign_recipients(build_query({'operator': 'AND', 'children': [{'field': 'id', 'lookup': 'in', 'value': f'{other_user.id}'}]}), campaign_id=other.id)
        NotificationCampaignRecipient.objects.filter(campaign=campaign).update(
            status=NotificationCampaignRecipientStatus.SENT
        )
        NotificationCampaignRecipient.objects.filter(campaign=other).update(
            status=NotificationCampaignRecipientStatus.FAILED
        )

        assert get_campaign_recipient_stats(campaign.id) == {
            'recipient_count': 1,
            'sent_count': 1,
            'failed_count': 0,
        }
        assert get_campaign_recipient_stats(other.id) == {
            'recipient_count': 1,
            'sent_count': 0,
            'failed_count': 1,
        }


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
            Q(**{'id__in': [high.id, low.id, zero.id, flagged.id, spam.id]}),
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
            Q(**{'id__in': [u.id for u in users]}),
            campaign_id=campaign.id,
        )

        batches = list(get_campaign_recipient_batches(campaign_id=campaign.id, batch_size=2))
        assert [len(batch) for batch in batches] == [2, 2, 1]
        flat = {recipient_id for batch in batches for recipient_id in batch}
        assert len(flat) == 5

    def test_restart_failed_only_returns_failed(self, campaign, users_and_recipients):
        data = users_and_recipients
        failed = NotificationCampaignRecipient.objects.get(campaign=campaign, user=data['high'])
        failed.status = NotificationCampaignRecipientStatus.FAILED
        failed.save(update_fields=['status'])

        pending_ids = _recipient_user_ids(campaign.id, spam=False, min_activity=data['threshold'])
        assert data['high'].id not in pending_ids

        failed_ids = _recipient_user_ids(campaign.id, restart_failed=True)
        assert failed_ids == [data['high'].id]

    def test_ignore_conflicts_on_duplicate_create(self, campaign):
        user = UserFactory()
        _set_activity(user, 10)
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        assert NotificationCampaignRecipient.objects.filter(campaign=campaign).count() == 1


class TestNotificationCampaignStart:

    @mock.patch('osf.email.notification_campaign.start_notification_campaign.delay')
    def test_campaign_start_sets_running_state(self, mock_delay, campaign):
        with mock.patch(
            'osf.models.notification_campaign.transaction.on_commit',
            side_effect=lambda callback: callback(),
        ):
            campaign.start()

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.RUNNING
        assert campaign.run_id is not None
        assert campaign.started_at is not None
        assert campaign.retries == 0
        mock_delay.assert_called_once_with(
            campaign_id=campaign.id,
            restart_failed=False,
            restart_stuck=False,
        )

    @mock.patch('osf.email.notification_campaign.start_notification_campaign.delay')
    def test_campaign_start_restart_stuck_counts(self, mock_delay, campaign):
        campaign.recipient_count = 10
        campaign.sent_count = 4
        campaign.failed_count = 4
        campaign.retries = 1
        campaign.save()

        with mock.patch(
            'osf.models.notification_campaign.transaction.on_commit',
            side_effect=lambda callback: callback(),
        ):
            campaign.start(restart_stuck=True)

        campaign.refresh_from_db()
        assert campaign.recipient_count == 10
        assert campaign.sent_count == 4
        assert campaign.failed_count == 0
        assert campaign.retries == 0
        mock_delay.assert_called_once_with(
            campaign_id=campaign.id,
            restart_failed=False,
            restart_stuck=True,
        )

    @mock.patch('osf.email.notification_campaign.chain')
    def test_start_creates_recipients_and_schedules_workflow(self, mock_chain, campaign):
        high = UserFactory()
        low = UserFactory()
        spam = UserFactory()
        spam.spam_status = SpamStatus.SPAM
        spam.save()
        _set_activity(high, 250)
        _set_activity(low, 10)

        campaign.metadata['filters'] = {
            'manual': {'operator': 'AND', 'children': [{'field': 'id', 'lookup': 'in', 'value': f'{high.id},{low.id},{spam.id}'}]},
        }
        campaign.run_id = uuid.uuid4()
        campaign.save()

        mock_chain.return_value.apply_async = mock.Mock()

        start_notification_campaign(campaign.id)

        campaign.refresh_from_db()
        recipients = {
            r.user_id: r.activity_score
            for r in NotificationCampaignRecipient.objects.filter(campaign=campaign)
        }
        assert recipients == {high.id: 250, low.id: 10, spam.id: 0}
        assert campaign.recipient_count == 3
        mock_chain.assert_called_once()
        mock_chain.return_value.apply_async.assert_called_once()

    @mock.patch('osf.email.notification_campaign.chain')
    def test_start_restart_failed_does_not_recreate_recipients(self, mock_chain, campaign):
        user = UserFactory()
        _set_activity(user, 50)
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=campaign, user=user)
        recipient.status = NotificationCampaignRecipientStatus.FAILED
        recipient.save(update_fields=['status'])

        campaign.run_id = uuid.uuid4()
        campaign.metadata['filters'] = {
            'manual': {'operator': 'AND', 'children': [{'field': 'id', 'lookup': 'in', 'value': str(user.id)}]},
        }
        campaign.save()
        mock_chain.return_value.apply_async = mock.Mock()

        start_notification_campaign(campaign.id, restart_failed=True)

        assert NotificationCampaignRecipient.objects.filter(campaign=campaign).count() == 1
        assert NotificationCampaignRecipient.objects.get(pk=recipient.pk).status == NotificationCampaignRecipientStatus.FAILED

    @mock.patch('osf.email.notification_campaign.chain')
    def test_start_restart_stuck_does_not_recreate_recipients(self, mock_chain, campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        campaign.run_id = uuid.uuid4()
        campaign.recipient_count = 1
        campaign.save()
        mock_chain.return_value.apply_async = mock.Mock()

        start_notification_campaign(campaign.id, restart_stuck=True)

        assert NotificationCampaignRecipient.objects.filter(campaign=campaign).count() == 1
        campaign.refresh_from_db()
        assert campaign.recipient_count == 1


class TestSendCampaignBatch:

    @pytest.fixture
    def running_campaign(self, campaign):
        campaign.run_id = uuid.uuid4()
        campaign.started_at = timezone.now()
        campaign.status = NotificationCampaignStatus.RUNNING
        campaign.save()
        return campaign

    @mock.patch.object(NotificationType, 'emit')
    def test_send_campaign_batch_marks_recipients_sent(self, mock_emit, running_campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        running_campaign.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.SENT
        assert running_campaign.sent_count == 1
        mock_emit.assert_called_once()

    @mock.patch.object(NotificationType, 'emit', side_effect=Exception('send failed'))
    @mock.patch('osf.email.notification_campaign.sentry.log_exception')
    def test_send_campaign_batch_marks_recipients_failed(self, mock_sentry, mock_emit, running_campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        running_campaign.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.FAILED
        assert 'send failed' in recipient.error_message
        assert running_campaign.failed_count == 1

    def test_send_campaign_batch_skips_invalid_email_addresses(self, running_campaign):
        user = UserFactory()
        user.username = 'asd'
        user.save(update_fields=['username'])
        user.emails.all().delete()

        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        running_campaign.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.SKIPPED
        assert recipient.error_message == 'Invalid email address'
        assert running_campaign.failed_count == 1
        assert running_campaign.sent_count == 0

    @mock.patch('osf.email.notification_campaign.send_email_with_send_grid')
    def test_send_campaign_batch_sendgrid_bulk_success(self, mock_sendgrid, running_campaign):
        user = UserFactory()
        running_campaign.metadata['sendgrid_bulk'] = True
        running_campaign.save(update_fields=['metadata'])
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        running_campaign.refresh_from_db()
        mock_sendgrid.assert_called_once()
        assert recipient.status == NotificationCampaignRecipientStatus.SENT
        assert running_campaign.sent_count == 1
        assert running_campaign.failed_count == 0

    @mock.patch(
        'osf.email.notification_campaign.send_email_with_send_grid',
        side_effect=Exception('bulk failed'),
    )
    @mock.patch('osf.email.notification_campaign.sentry.log_exception')
    def test_send_campaign_batch_sendgrid_bulk_failure(self, mock_sentry, mock_sendgrid, running_campaign):
        user = UserFactory()
        running_campaign.metadata['sendgrid_bulk'] = True
        running_campaign.save(update_fields=['metadata'])
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        running_campaign.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.FAILED
        assert running_campaign.failed_count == 1
        assert running_campaign.sent_count == 0

    @mock.patch('osf.email.notification_campaign.sentry.log_message')
    def test_send_campaign_batch_logs_when_time_window_exceeded(self, mock_sentry, running_campaign):
        user = UserFactory()
        running_campaign.started_at = timezone.now() - timedelta(hours=9)
        running_campaign.metadata['execution']['time_window'] = 8
        running_campaign.save()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        with mock.patch.object(NotificationType, 'emit'):
            send_campaign_batch(
                context={},
                recipients_ids=[recipient.id],
                notification_type_name='blank',
                campaign_id=running_campaign.id,
                run_id=running_campaign.run_id,
            )

        running_campaign.refresh_from_db()
        assert running_campaign.developer_reminder_sent is True
        mock_sentry.assert_called_once()

    def test_send_campaign_batch_marks_failed_when_notification_type_missing(self, running_campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='does-not-exist',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        running_campaign.refresh_from_db()
        recipient.refresh_from_db()
        assert running_campaign.status == NotificationCampaignStatus.FAILED
        assert recipient.status == NotificationCampaignRecipientStatus.PENDING

    def test_send_campaign_batch_skips_stale_run_id(self, running_campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=uuid.uuid4(),
        )

        recipient.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.PENDING

    def test_send_campaign_batch_skips_cancelled_campaign(self, running_campaign):
        user = UserFactory()
        running_campaign.status = NotificationCampaignStatus.CANCELLED
        running_campaign.save(update_fields=['status'])
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.PENDING

    @mock.patch.object(NotificationType, 'emit')
    def test_send_campaign_batch_uses_fallback_email_when_username_has_no_at(self, mock_emit, running_campaign):
        user = UserFactory()
        user.username = 'invalid'
        user.save(update_fields=['username'])
        user.emails.all().delete()
        user.emails.create(address='fallback@example.com')

        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=running_campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=running_campaign, user=user)

        send_campaign_batch(
            context={},
            recipients_ids=[recipient.id],
            notification_type_name='blank',
            campaign_id=running_campaign.id,
            run_id=running_campaign.run_id,
        )

        recipient.refresh_from_db()
        running_campaign.refresh_from_db()
        assert recipient.status == NotificationCampaignRecipientStatus.SENT
        assert running_campaign.sent_count == 1
        assert running_campaign.failed_count == 0
        mock_emit.assert_called_once()


class TestNotificationCampaignCancel:

    def test_cancel_sets_cancelled_status_and_completed_at(self, campaign):
        assert campaign.completed_at is None

        campaign.cancel()

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.CANCELLED
        assert campaign.completed_at is not None

    def test_cancel_does_not_overwrite_existing_completed_at(self, campaign):
        completed_at = timezone.now() - timedelta(hours=1)
        campaign.completed_at = completed_at
        campaign.save(update_fields=['completed_at'])

        campaign.cancel()

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.CANCELLED
        assert campaign.completed_at == completed_at


class TestProcessCampaignRetry:

    def test_process_campaign_retry_marks_completed_and_aggregates_stats(self, campaign):
        sent_user = UserFactory()
        skipped_user = UserFactory()
        create_campaign_recipients(
            Q(**{'id__in': [sent_user.id, skipped_user.id]}),
            campaign_id=campaign.id,
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=sent_user).update(
            status=NotificationCampaignRecipientStatus.SENT
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=skipped_user).update(
            status=NotificationCampaignRecipientStatus.SKIPPED
        )
        campaign.run_id = uuid.uuid4()
        campaign.save(update_fields=['run_id'])

        process_campaign_retry(campaign_id=campaign.id, run_id=campaign.run_id)

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.COMPLETED
        assert campaign.recipient_count == 2
        assert campaign.sent_count == 1
        assert campaign.failed_count == 1
        assert campaign.completed_at is not None

    def test_process_campaign_retry_skips_stale_run_id(self, campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        NotificationCampaignRecipient.objects.filter(campaign=campaign).update(
            status=NotificationCampaignRecipientStatus.SENT
        )
        campaign.run_id = uuid.uuid4()
        campaign.status = NotificationCampaignStatus.RUNNING
        campaign.save()

        process_campaign_retry(campaign_id=campaign.id, run_id=uuid.uuid4())

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.RUNNING
        assert campaign.completed_at is None
        assert campaign.sent_count == 0

    @mock.patch('osf.email.notification_campaign.sentry.log_message')
    def test_process_campaign_retry_keeps_cancelled_status_and_syncs_stats(self, mock_sentry, campaign):
        sent_user = UserFactory()
        failed_user = UserFactory()
        create_campaign_recipients(
            Q(**{'id__in': [sent_user.id, failed_user.id]}),
            campaign_id=campaign.id,
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=sent_user).update(
            status=NotificationCampaignRecipientStatus.SENT
        )
        NotificationCampaignRecipient.objects.filter(campaign=campaign, user=failed_user).update(
            status=NotificationCampaignRecipientStatus.FAILED
        )
        campaign.run_id = uuid.uuid4()
        campaign.status = NotificationCampaignStatus.CANCELLED
        campaign.save()

        process_campaign_retry(campaign_id=campaign.id, run_id=campaign.run_id)

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.CANCELLED
        assert campaign.recipient_count == 2
        assert campaign.sent_count == 1
        assert campaign.failed_count == 1
        assert campaign.completed_at is not None
        mock_sentry.assert_called_once()

    @mock.patch('osf.email.notification_campaign.chain')
    def test_process_campaign_retry_retries_failed_recipients(self, mock_chain, campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=campaign, user=user)
        recipient.status = NotificationCampaignRecipientStatus.FAILED
        recipient.save(update_fields=['status'])
        campaign.run_id = uuid.uuid4()
        campaign.retries = 0
        campaign.status = NotificationCampaignStatus.RUNNING
        campaign.save()
        mock_chain.return_value.apply_async = mock.Mock()

        process_campaign_retry(campaign_id=campaign.id, run_id=campaign.run_id)

        campaign.refresh_from_db()
        assert campaign.retries == 1
        assert campaign.status == NotificationCampaignStatus.RUNNING
        mock_chain.assert_called_once()

    def test_process_campaign_retry_marks_partially_completed_after_max_retries(self, campaign):
        user = UserFactory()
        create_campaign_recipients(Q(**{'id__in': [user.id]}), campaign_id=campaign.id)
        recipient = NotificationCampaignRecipient.objects.get(campaign=campaign, user=user)
        recipient.status = NotificationCampaignRecipientStatus.FAILED
        recipient.save(update_fields=['status'])
        campaign.run_id = uuid.uuid4()
        campaign.retries = 2
        campaign.save()

        process_campaign_retry(campaign_id=campaign.id, run_id=campaign.run_id)

        campaign.refresh_from_db()
        assert campaign.status == NotificationCampaignStatus.PARTIALLY_COMPLETED
        assert campaign.failed_count == 1
        assert campaign.recipient_count == 1
        assert campaign.completed_at is not None
