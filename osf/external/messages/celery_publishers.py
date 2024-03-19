from kombu import Exchange
from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task


def publish_deactivated_user(user):
    enqueue_task(
        _publish_user_status_change.s(
            body={
                'action': 'deactivate',
                'user_uri': user.get_semantic_iri(),
            },
        )
    )


def publish_reactivate_user(user):
    enqueue_task(
        _publish_user_status_change.s(
            body={
                'action': 'reactivate',
                'user_uri': user.get_semantic_iri(),
            },
        )
    )


def publish_merged_user(user):
    assert user.merged_by, 'User received merge signal, but has no `merged_by` reference.'
    enqueue_task(
        _publish_user_status_change.s(
            body={
                'action': 'merge',
                'user_uri': user.get_semantic_iri(),
                'merged_user_uri': user.merged_by.get_semantic_iri(),
            },
        )
    )


@celery_app.task()
def _publish_user_status_change(body: dict):
    with celery_app.producer_pool.acquire() as producer:
        producer.publish(
            body=body,
            exchange=Exchange(celery_app.conf.task_account_status_changes_queue),
            serializer='json'
        )
