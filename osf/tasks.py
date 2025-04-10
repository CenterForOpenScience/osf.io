import logging
import re

from django.db.models import Model

from framework.celery_tasks import app

logger = logging.getLogger(__name__)
iri_regex = re.compile(r'http://[^/]+/(?P<id>\w{5})/?')

def get_object_by_url(url: str, model: type[Model]) -> Model | None:
    if match := iri_regex.match(url):
        return model.objects.get(guids___id=match['id'])
    raise Exception(f"Invalid URL received: {url=}")

@app.task(max_retries=5, name='osf.tasks.log_gv_addon', default_retry_delay=10)
def log_gv_addon(node_url: str, action: str, user_url: str, addon: str):
    from osf.models import NodeLog, OSFUser, Node
    PERMITTED_GV_ACTIONS = frozenset({
        NodeLog.ADDON_ADDED,
        NodeLog.ADDON_REMOVED
    })
    if action not in PERMITTED_GV_ACTIONS:
        logger.error(f"{action} is not permitted to be logged from GV")
        return
    try:
        node = get_object_by_url(node_url, Node)
        user = get_object_by_url(user_url, OSFUser)
    except Exception as e:
        logger.error(e)
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
