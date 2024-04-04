from django.apps import apps

from osf.utils.requests import requests_retry_session
from framework.celery_tasks import app
from framework.postcommit_tasks.handlers import get_task_from_postcommit_queue, enqueue_postcommit_task
from osf.utils.workflows import RegistrationModerationStates

from website import settings


@app.task(max_retries=5, default_retry_delay=60, ignore_results=False)
def _archive_to_ia(node_id):
    requests_retry_session().post(f'{settings.OSF_PIGEON_URL}archive/{node_id}')

def archive_to_ia(node):
    if settings.IA_ARCHIVE_ENABLED:
        enqueue_postcommit_task(_archive_to_ia, (node._id,), {}, celery=True)

@app.task(max_retries=5, default_retry_delay=60, ignore_results=False)
def _update_ia_metadata(node_id, data):
    requests_retry_session().post(f'{settings.OSF_PIGEON_URL}metadata/{node_id}', json=data).raise_for_status()

def update_ia_metadata(node, data=None):
    """
    This debounces/throttles requests by grabbing a pending task and overriding it instead of making a new one every
    pre-commit m2m change.

    IA wants us to brand our specific osf metadata with a `osf_` prefix. So we are following IA_MAPPED_NAMES.
    """
    if settings.IA_ARCHIVE_ENABLED:

        Registration = apps.get_model('osf.registration')
        if not data:
            allowed_metadata = Registration.SYNCED_WITH_IA.intersection(node.get_dirty_fields().keys())
            data = {key: str(getattr(node, key)) for key in allowed_metadata}
        data = {
            Registration.IA_MAPPED_NAMES.get(key, key): data[key] for key in data
        }

        if node.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name:
            data['withdrawal_justification'] = node.withdrawal_justification

        if getattr(node, 'ia_url', None) and node.is_public:
            task = get_task_from_postcommit_queue(
                'framework.celery_tasks._update_ia_metadata',
                predicate=lambda task: task.args[0] == node._id and data.keys() == task.args[1].keys()
            )
            if task:
                task.args = (node._id, data, )
            else:
                enqueue_postcommit_task(_update_ia_metadata, (node._id, data, ), {}, celery=True)
