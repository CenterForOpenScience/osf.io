import django
django.setup()

from website.app import init_app
init_app(routes=False)

from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from osf.models import OSFUser, NotificationSubscription, NotificationType


@celery_app.task(name='scripts.populate_notification_subscriptions_user_global_file_updated')
def populate_notification_subscriptions_user_global_file_updated(per_last_years: int=None, batch_size=1000):
    print('---Starting USER_FILE_UPDATED subscriptions population script----')
    global_start = datetime.now()

    user_file_updated_nt = NotificationType.Type.USER_FILE_UPDATED

    user_ct = ContentType.objects.get_for_model(OSFUser)
    if per_last_years:
        one_year_ago = timezone.now() - timedelta(days=365 * per_last_years)
        user_qs = (OSFUser.objects
            .filter(last_login__gte=one_year_ago)
            .exclude(subscriptions__notification_type__name=user_file_updated_nt)
            .distinct('id')
            .order_by('id')
            .iterator(chunk_size=batch_size)
        )
    else:
        user_qs = (OSFUser.objects
            .exclude(subscriptions__notification_type__name=user_file_updated_nt)
            .distinct('id')
            .order_by('id')
            .iterator(chunk_size=batch_size)
        )

    items_to_create = []
    total_created = 0

    batch_start = datetime.now()
    for count, user in enumerate(user_qs, 1):
        items_to_create.append(
            NotificationSubscription(
                notification_type=user_file_updated_nt.instance,
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
    print(f'Total time for USER_FILE_UPDATED subscription population: {global_end - global_start}')
    print(f'Created {total_created} subscriptions.')
    print('----Creation finished----')

@celery_app.task(name='scripts.update_notification_subscriptions_user_global_file_updated')
def update_notification_subscriptions_user_global_file_updated():
    print('---Starting USER_FILE_UPDATED subscriptions updating script----')

    user_file_updated_nt = NotificationType.Type.USER_FILE_UPDATED

    update_start = datetime.now()
    updated = (
        NotificationSubscription.objects
        .filter(
            notification_type__name=user_file_updated_nt,
            _is_digest=False,
        )
        .update(_is_digest=True)
    )
    update_end = datetime.now()

    print(f'Updated {updated} subscriptions. Took time: {update_end - update_start}')
    print('Update finished.')