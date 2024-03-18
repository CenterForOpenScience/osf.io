from kombu import Exchange
from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task


def publish_deactivated_user(user):
    enqueue_task(
        _publish_user_status_change.s(
            body={
                'action': 'deactivate',
                'user_uri': user.url,
            },
        )
    )


def publish_reactivate_user(user):
    enqueue_task(
        _publish_user_status_change.s(
            body={
                'action': 'reactivate',
                'user_uri': user.url,
            },
        )
    )


def publish_merged_user(user):
    assert user.merged_by, 'User received merge signal, but has no `merged_by` reference.'
    enqueue_task(
        _publish_user_status_change.s(
            body={
                'action': 'merge',
                'user_uri': user.url,
                'merged_user_uri': user.merged_by.url,
            },
        )
    )


@celery_app.task()
def _publish_user_status_change(body: dict):
    with celery_app.producer_pool.acquire() as producer:
        producer.publish(
            body=body,
            exchange=Exchange(celery_app.conf.account_status_changes),
            serializer='json'
        )
