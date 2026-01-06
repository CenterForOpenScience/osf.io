import django
django.setup()

from website.app import init_app
init_app(routes=False)

from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, OuterRef, Subquery, IntegerField, CharField
from django.db.models.functions import Cast
from osf.models import OSFUser, Node, NotificationSubscription, NotificationType


@celery_app.task(name='scripts.populate_subscriptions')
def populate_subscriptions():
    created = 0
    user_file_nt = NotificationType.Type.USER_FILE_UPDATED.instance
    review_nt = NotificationType.Type.REVIEWS_SUBMISSION_STATUS.instance
    node_file_nt = NotificationType.Type.NODE_FILE_UPDATED.instance

    user_ct = ContentType.objects.get_for_model(OSFUser)
    node_ct = ContentType.objects.get_for_model(Node)

    reviews_qs = OSFUser.objects.exclude(subscriptions__notification_type__name=NotificationType.Type.REVIEWS_SUBMISSION_STATUS).distinct('id')
    files_qs = OSFUser.objects.exclude(subscriptions__notification_type__name=NotificationType.Type.USER_FILE_UPDATED).distinct('id')

    node_notifications_sq = (
        NotificationSubscription.objects.filter(
            content_type=node_ct,
            notification_type=node_file_nt,
            object_id=Cast(OuterRef('pk'), CharField()),
        ).values(
            'object_id'
        ).annotate(
            cnt=Count('id')
        ).values('cnt')[:1]
    )

    nodes_qs = (
        Node.objects
        .annotate(
            contributors_count=Count('_contributors', distinct=True),
            notifications_count=Subquery(
                node_notifications_sq,
                output_field=IntegerField(),
            ),
        )
        .exclude(contributors_count=F('notifications_count'))
    )

    for user in reviews_qs:
        _, is_created = NotificationSubscription.objects.get_or_create(
            notification_type=review_nt,
            user=user,
            content_type=user_ct,
            object_id=user.id,
            message_frequency='instantly',
        )
        if is_created:
            created += 1

    for user in files_qs:
        _, is_created = NotificationSubscription.objects.get_or_create(
            notification_type=user_file_nt,
            user=user,
            content_type=user_ct,
            object_id=user.id,
            message_frequency='instantly',
        )
        if is_created:
            created += 1

    for node in nodes_qs:
        for contributor in node.contributors.all():
            try:
                _, is_created = NotificationSubscription.objects.get_or_create(
                    notification_type=node_file_nt,
                    user=contributor,
                    content_type=node_ct,
                    object_id=node.id,
                    defaults={
                        'message_frequency': 'instantly',
                    },
                )
                if is_created:
                    created += 1
            except Exception:
                continue

    print(f"Created {created} subscriptions")

if __name__ == '__main__':
    populate_subscriptions.delay()
