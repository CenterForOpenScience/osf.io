import django
django.setup()

from website.app import init_app
init_app(routes=False)

from datetime import datetime
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, OuterRef, Subquery, IntegerField, CharField
from django.db.models.functions import Cast, Coalesce
from osf.models import  Node, NotificationSubscription, NotificationType


@celery_app.task(name='scripts.populate_nodes_notification_subscriptions')
def populate_nodes_notification_subscriptions():
    print('---Starting NODE_FILE_UPDATED subscriptions population script----')
    global_start = datetime.now()

    batch_size = 1000
    node_file_nt = NotificationType.Type.NODE_FILE_UPDATED

    node_ct = ContentType.objects.get_for_model(Node)

    node_notifications_sq = (
        NotificationSubscription.objects.filter(
            content_type=node_ct,
            notification_type=node_file_nt.instance,
            object_id=Cast(OuterRef('pk'), CharField()),
        ).values(
            'object_id'
        ).annotate(
            cnt=Count('id')
        ).values('cnt')[:1]
    )

    nodes_qs = (
        Node.objects
        .filter(is_deleted=False)
        .annotate(
            contributors_count=Count('_contributors', distinct=True),
            notifications_count=Coalesce(
                Subquery(
                    node_notifications_sq,
                    output_field=IntegerField(),
                ),
                0
            ),
        ).exclude(contributors_count=F('notifications_count'))
    ).iterator(chunk_size=batch_size)

    items_to_create = []
    total_created = 0
    batch_start = datetime.now()
    count_nodes = 0
    count_contributors = 0
    for node in nodes_qs:
        count_nodes += 1
        for contributor in node.contributors.all():
            count_contributors += 1
            items_to_create.append(
                NotificationSubscription(
                    notification_type=node_file_nt.instance,
                    user=contributor,
                    content_type=node_ct,
                    object_id=node.id,
                    _is_digest=True,
                    message_frequency='none',
                )
            )
            if len(items_to_create) >= batch_size:
                print(f'Creating batch of {len(items_to_create)} subscriptions...')
                try:
                    NotificationSubscription.objects.bulk_create(
                        items_to_create,
                        batch_size=batch_size,
                        ignore_conflicts=True,
                    )
                    total_created += len(items_to_create)
                    items_to_create = []
                except Exception as exeption:
                    print(f"Error during bulk_create: {exeption}")
                    continue
                finally:
                    items_to_create.clear()
                batch_end = datetime.now()
                print(f'Batch took {batch_end - batch_start}')

                if count_contributors % batch_size == 0:
                    print(f'Processed {count_nodes} nodes with {count_contributors} contributors, created {total_created} subscriptions')

    if items_to_create:
        print(f'Creating final batch of {len(items_to_create)} subscriptions...')
        try:
            NotificationSubscription.objects.bulk_create(
                items_to_create,
                batch_size=batch_size,
                ignore_conflicts=True,
            )
            total_created += len(items_to_create)
        except Exception as exeption:
            print(f"Error during bulk_create: {exeption}")

    global_end = datetime.now()
    print(f'Total time for NODE_FILE_UPDATED subscription population: {global_end - global_start}')
    print(f'Created {total_created} subscriptions.')
    print('----Creation finished----')

@celery_app.task(name='scripts.update_nodes_notification_subscriptions')
def update_nodes_notification_subscriptions():
    print('---Starting NODE_FILE_UPDATED subscriptions update script----')

    node_file_nt = NotificationType.Type.NODE_FILE_UPDATED

    updated_start = datetime.now()
    updated = (
        NotificationSubscription.objects.filter(
            notification_type__name=node_file_nt,
            _is_digest=False,
        )
        .update(_is_digest=True)
    )
    updated_end = datetime.now()
    print(f'Updated {updated} subscriptions. Took time: {updated_end - updated_start}')
    print('Update finished.')