import django
django.setup()

from website.app import init_app
init_app(routes=False)

from datetime import datetime
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from osf.models import OSFUser, NotificationSubscription, NotificationType


@celery_app.task(name='scripts.populate_reviews_notification_subscriptions')
def populate_reviews_notification_subscriptions():
    print('---Starting REVIEWS_SUBMISSION_STATUS subscriptions population script----')
    global_start = datetime.now()

    batch_size = 1000
    review_nt = NotificationType.Type.REVIEWS_SUBMISSION_STATUS

    user_ct = ContentType.objects.get_for_model(OSFUser)

    user_qs = OSFUser.objects.exclude(
        subscriptions__notification_type__name=NotificationType.Type.REVIEWS_SUBMISSION_STATUS.instance
    ).distinct('id')

    items_to_create = []
    total_created = 0
    batch_start = datetime.now()
    for count, user in enumerate(user_qs, 1):
        items_to_create.append(
            NotificationSubscription(
                notification_type=review_nt.instance,
                user=user,
                content_type=user_ct,
                object_id=user.id,
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
            except Exception as e:
                print(f'Error during bulk_create: {e}')
            finally:
                items_to_create.clear()
            batch_end = datetime.now()
            print(f'Batch took {batch_end - batch_start}')

            if count % batch_size == 0:
                print(f'Processed {count}, created {total_created}')
            batch_start = datetime.now()

    if items_to_create:
        print(f'Creating final batch of {len(items_to_create)} subscriptions...')
        try:
            NotificationSubscription.objects.bulk_create(
                items_to_create,
                batch_size=batch_size,
                ignore_conflicts=True,
            )
            total_created += len(items_to_create)
        except Exception as e:
            print(f'Error during bulk_create: {e}')

    global_end = datetime.now()
    print(f'Total time for REVIEWS_SUBMISSION_STATUS subscription population: {global_end - global_start}')
    print(f'Created {total_created} subscriptions.')
    print('----Creation finished----')

@celery_app.task(name='scripts.update_reviews_notification_subscriptions')
def update_reviews_notification_subscriptions():
    print('---Starting REVIEWS_SUBMISSION_STATUS subscriptions updating script----')

    review_nt = NotificationType.Type.REVIEWS_SUBMISSION_STATUS

    updated_start = datetime.now()
    updated = (
        NotificationSubscription.objects.filter(
            notification_type__name=review_nt,
            _is_digest=False,
        )
        .update(_is_digest=True)
    )
    updated_end = datetime.now()

    print(f'Updated {updated} subscriptions. Took time: {updated_end - updated_start}')
    print('Update finished.')
