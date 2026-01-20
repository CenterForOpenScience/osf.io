import django
django.setup()

from website.app import init_app
init_app(routes=False)

from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from osf.models import OSFUser, NotificationSubscription, NotificationType


@celery_app.task(name="scripts.populate_notification_subscriptions_user_global_file_updated")
def populate_notification_subscriptions_user_global_file_updated():
    print("Starting USER_FILE_UPDATED subscription population...")

    batch_size = 1000
    user_file_updated_nt = NotificationType.Type.USER_FILE_UPDATED

    updated = (
        NotificationSubscription.objects
        .filter(
            notification_type__name=user_file_updated_nt,
            _is_digest=False,
        )
        .update(_is_digest=True)
    )

    print(f"Updated {updated} subscriptions")
    print("Update finished.")

    user_ct = ContentType.objects.get_for_model(OSFUser)
    user_qs = (OSFUser.objects
        .exclude(subscriptions__notification_type__name=user_file_updated_nt)
        .distinct()
        .order_by("id")
        .iterator(chunk_size=batch_size)
    )

    items_to_create = []
    total_created = 0

    for count, user in enumerate(user_qs, 1):
        items_to_create.append(
            NotificationSubscription(
                notification_type=user_file_updated_nt.instance,
                user=user,
                content_type=user_ct,
                object_id=user.id,
                _is_digest=True,
                message_frequency="none",
            )
        )
        if len(items_to_create) >= batch_size:
            print(f"Creating batch of {len(items_to_create)} subscriptions...")
            NotificationSubscription.objects.bulk_create(
                items_to_create,
                batch_size=batch_size,
                ignore_conflicts=True,
            )
            total_created += len(items_to_create)
            items_to_create.clear()

            if count % 1000 == 0:
                print(f"Processed {count}, created {total_created}")

    if items_to_create:
        print(f"Creating final batch of {len(items_to_create)} subscriptions...")
        NotificationSubscription.objects.bulk_create(
            items_to_create,
            batch_size=batch_size,
            ignore_conflicts=True,
        )
        total_created += len(items_to_create)

    print(f"Created {total_created} subscriptions.")
    print("Creation finished.")
