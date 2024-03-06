from framework.celery_tasks import app as celery_app
from kombu import Exchange


def publish_deactivated_user(user):
    _publish_user_status_change(
        body={
            'user_uri': user.url,
        },
        routing_key=celery_app.conf.DEACTIVATED_ROUTING_KEY
    )


def publish_reactivate_user(user):
    _publish_user_status_change(
        body={
            'user_uri': user.url,
        },
        routing_key=celery_app.conf.REACTIVATED_ROUTING_KEY
    )


def publish_merged_user(user):
    _publish_user_status_change(
        body={
            'user_uri': user.url,
            'merged_user_uri': user.merged_by.url,
        },
        routing_key=celery_app.conf.MERGED_ROUTING_KEY
    )


def _publish_user_status_change(body, routing_key):
    with celery_app.producer_pool.acquire(block=True) as producer:
        producer.publish(
            body=body,
            exchange=Exchange(celery_app.conf.account_status_changes),
            routing_key=routing_key,
            serializer='json'
        )
