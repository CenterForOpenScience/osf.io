import logging
import uuid
from itertools import batched

from django.db.models import BooleanField, Count, OuterRef, Q, Subquery, Exists
from django.db.models.functions import Coalesce
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import Email, OSFUser, UserActivityCounter, Contributor
from osf.models.notification_campaign import (
    NotificationCampaign,
    NotificationCampaignRecipient,
    NotificationCampaignRecipientStatus,
)
from osf.models.spam import SpamStatus

logger = logging.getLogger(__name__)

BULK_CREATE_SIZE = 5000
FILTER_PRESETS = {
    'all': {},
    'active': {'is_active': True},
    'internal': {'is_active': True, 'is_staff': True, 'username__endswith': '@cos.io'},
}

first_email_subquery = (
    Email.objects
    .filter(user=OuterRef('user_id'))
    .values('address')[:1]
)


counter_subquery = (
    UserActivityCounter.objects
    .filter(_id=OuterRef('guids___id'))
    .values('total')[:1]
)


# Matches users who contribute to at least one project or component
# Counts: projects and components at any nesting depth - all share the osf.node type
# Does not count: registrations, draft nodes, and preprints, whose contributors live in a
# separate table entirely
# not filtered on: contributor permissions, whether the project is public, and
# whether the node is deleted or spam-flagged
project_contributor_subquery = Contributor.objects.filter(user_id=OuterRef('pk'), node__type='osf.node')


def build_query(node):
    """
    Convert a filter tree into a Django Q object.
    """

    if 'field' in node:
        value = node['value']
        lookup = node['lookup']
        negated_lookups = {  # not native Django field lookups
            'not_contains': 'contains',
            'not_icontains': 'icontains',
        }

        if lookup == 'in':
            value = [v.strip() for v in value.split(',')]

        if lookup == 'isnull':
            value = BooleanField().to_python(value)

        if lookup in negated_lookups:
            return ~Q(**{
                f'{node["field"]}__{negated_lookups[lookup]}': value
            })

        return Q(**{
            f'{node["field"]}__{lookup}': value
        })

    operator = node.get('operator', 'AND')
    children = node.get('children', [])

    if not children:
        return Q()

    query = build_query(children[0])

    for child in children[1:]:
        if operator == 'AND':
            query &= build_query(child)
        else:
            query |= build_query(child)

    return query


def build_campaign_filter_query(filters):
    """AND together optional predefined, manual and contributor filter clauses."""
    filters = filters or {}
    query = Q()
    if predefined := filters.get('predefined'):
        query &= Q(**FILTER_PRESETS.get(predefined, {}))
    if manual := filters.get('manual'):
        query &= build_query(manual)
    if filters.get('exclude_non_contributors'):
        query &= Q(Exists(project_contributor_subquery))
    return query


@celery_app.task(name='email.create_campaign_recipients')
def create_campaign_recipients(filters=None, campaign_id=None):
    recipients_creation_started_at = timezone.now()
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    if not filters:

        raw_filters = campaign.metadata.get('filters', {})
        filters = build_campaign_filter_query(raw_filters)

    qs = (
        OSFUser.objects
        .filter(filters)
        .annotate(activity_score=Coalesce(Subquery(counter_subquery), 0))
        .values_list(
            'id',
            'activity_score',
        )
    )
    processed_records = 0

    for rows in batched(qs.iterator(chunk_size=BULK_CREATE_SIZE), BULK_CREATE_SIZE):
        NotificationCampaignRecipient.objects.bulk_create(
            [
                NotificationCampaignRecipient(
                    campaign_id=campaign_id,
                    user_id=user_id,
                    activity_score=activity_score,
                )
                for user_id, activity_score in rows
            ],
            update_conflicts=True,
            update_fields=['activity_score'],
            unique_fields=['campaign', 'user'],
        )
        processed_records += len(rows)

    campaign.recipient_count = processed_records
    campaign.metadata['recipients_creation_finished'] = True
    campaign.save()

    recipients_creation_finished_at = timezone.now()
    recipients_creation_run_time = (recipients_creation_finished_at - recipients_creation_started_at)
    message = (f'[Notification Campaign #{campaign_id}] INFO: '
                f'Recipients creation finished in {recipients_creation_run_time} seconds '
                f'(start={recipients_creation_started_at}, finish={recipients_creation_finished_at}) '
                f'for Campaign {campaign.name} (start={campaign.started_at}).')
    logger.info(message)
    sentry.log_message(message)


def get_campaign_recipient_stats(campaign_id):
    return NotificationCampaignRecipient.objects.filter(
        campaign_id=campaign_id
    ).aggregate(
        recipient_count=Count('id'),
        sent_count=Count(
            'id',
            filter=Q(status=NotificationCampaignRecipientStatus.SENT),
        ),
        failed_count=Count(
            'id',
            filter=Q(
                status__in=[
                    NotificationCampaignRecipientStatus.FAILED,
                    NotificationCampaignRecipientStatus.SKIPPED,
                ]
            ),
        ),
        queued_count=Count(
            'id',
            filter=Q(status=NotificationCampaignRecipientStatus.QUEUED),
        ),
        awaiting_count=Count(
            'id',
            filter=Q(status=NotificationCampaignRecipientStatus.AWAITING_DELIVERY),
        ),
    )


def assign_batch_id_to_recipients(
    campaign_id,
    batch_size,
    restart_failed=False,
    min_activity=None,
    max_activity=None,
    spam=None,
):
    batch_id = uuid.uuid4()
    filters = Q(campaign_id=campaign_id)

    if restart_failed:
        filters &= Q(
            status=NotificationCampaignRecipientStatus.FAILED,
        )
    else:
        filters &= Q(
            status=NotificationCampaignRecipientStatus.PENDING,
            batch_id__isnull=True,
        )

    if min_activity is not None:
        filters &= Q(activity_score__gte=min_activity)
    if max_activity is not None:
        filters &= Q(activity_score__lt=max_activity)

    if spam is not None:
        filters &= Q(user__spam_status=SpamStatus.SPAM) if spam else ~Q(user__spam_status=SpamStatus.SPAM)

    recipient_ids = NotificationCampaignRecipient.objects.filter(
        filters
    ).values_list('id', flat=True)[:batch_size]

    updated = NotificationCampaignRecipient.objects.filter(id__in=recipient_ids).update(batch_id=batch_id, status=NotificationCampaignRecipientStatus.QUEUED)

    if updated == 0:
        return None

    return batch_id
