import logging
import re

from django.db.models import Model

from framework.celery_tasks import app
from framework.sentry import log_message

logger = logging.getLogger(__name__)
iri_regex = re.compile(r'https?://[^/]+/(?P<id>\w{5})/?')

def get_object_by_url[T: Model](url: str, model: type[T]) -> T | None:
    if not (match := iri_regex.match(url)):
        log_message(f"received invalid {model.__name__} {url=}. ", skip_session=True)
        return None
    try:
        return model.objects.get(guids___id=match['id'])
    except model.DoesNotExist:
        log_message(f"Could not find {model.__name__} with id={match['id']}", skip_session=True)
        return None

@app.task(max_retries=5, name='osf.tasks.log_gv_addon', default_retry_delay=10)
def log_gv_addon(node_url: str, action: str, user_url: str, addon: str):
    from osf.models import NodeLog, OSFUser, Node

    PERMITTED_GV_ACTIONS = frozenset({
        NodeLog.ADDON_ADDED,
        NodeLog.ADDON_REMOVED
    })
    if action not in PERMITTED_GV_ACTIONS:
        log_message(f"{action} is not permitted to be logged from GV", skip_session=True)
        return

    node = get_object_by_url(node_url, Node)
    user = get_object_by_url(user_url, OSFUser)
    if not node or not user:
        return

    node.add_log(
        action=action,
        auth=user,
        params={
            'node': node._id,
            'project': node.parent_id,
            'addon': addon
        }
    )
