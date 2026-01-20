import django
django.setup()

from website.app import init_app
init_app(routes=False)

from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, OuterRef, Subquery, IntegerField, CharField
from django.db.models.functions import Cast
from osf.models import  Node, NotificationSubscription, NotificationType


@celery_app.task(name='scripts.populate_nodes_notification_subscriptions')
def populate_nodes_notification_subscriptions():
    created = 0
    node_file_nt = NotificationType.Type.NODE_FILE_UPDATED.instance

    node_ct = ContentType.objects.get_for_model(Node)

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
        ).exclude(contributors_count=F('notifications_count'))
    )

    print(f"Creating NODE_FILE_UPDATED subscriptions for {nodes_qs.count()} nodes.")
    for id, node in enumerate(nodes_qs, 1):
        print(f"Processing node {id} / {nodes_qs.count()}")
        for contributor in node.contributors.all():
            try:
                _, is_created = NotificationSubscription.objects.get_or_create(
                    notification_type=node_file_nt,
                    user=contributor,
                    content_type=node_ct,
                    object_id=node.id,
                    defaults={
                        '_is_digest': True,
                        'message_frequency': 'none',
                    },
                )
                if is_created:
                    created += 1
            except Exception as exeption:
                print(exeption)
                continue

    print(f"Created {created} subscriptions")

if __name__ == '__main__':
    populate_nodes_notification_subscriptions.delay()
