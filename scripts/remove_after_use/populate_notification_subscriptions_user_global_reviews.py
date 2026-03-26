import django
django.setup()

from website.app import init_app
init_app(routes=False)

from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from osf.models import OSFUser, NotificationSubscription, NotificationTypeEnum


@celery_app.task(name='scripts.remove_after_use.populate_notification_subscriptions_user_global_reviews')
def populate_notification_subscriptions_user_global_reviews(per_last_years: int | None = None, batch_size: int = 1000):
    print('---Starting REVIEWS_SUBMISSION_STATUS subscriptions population script----')
    global_start = datetime.now()

    review_nt = NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS
    user_ct = ContentType.objects.get_for_model(OSFUser)
    if per_last_years:
        from_date = timezone.now() - relativedelta(years=per_last_years)
        user_qs = OSFUser.objects.filter(date_last_login__gte=from_date).exclude(
            subscriptions__notification_type__name=review_nt.instance
        ).distinct('id')
    else:
        user_qs = OSFUser.objects.exclude(
            subscriptions__notification_type__name=review_nt.instance
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
        final_batch_start = datetime.now()
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
        final_batch_end = datetime.now()
        print(f'Final batch took {final_batch_end - final_batch_start}')

    global_end = datetime.now()
    print(f'Total time for REVIEWS_SUBMISSION_STATUS subscription population: {global_end - global_start}')
    print(f'Created {total_created} subscriptions.')
    print('----Creation finished----')

@celery_app.task(name='scripts.remove_after_use.update_notification_subscriptions_user_global_reviews')
def update_notification_subscriptions_user_global_reviews():
    print('---Starting REVIEWS_SUBMISSION_STATUS subscriptions updating script----')

    review_nt = NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS

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
