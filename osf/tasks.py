import logging

from framework.celery_tasks import app


logger = logging.getLogger(__name__)

@app.task(max_retries=5, name='osf.tasks.log_gv_addon', default_retry_delay=10)
def log_gv_addon(node_url: str, action: str, user_url: str, addon: str):
    from osf.models import NodeLog, OSFUser, Node
    PERMITTED_GV_ACTIONS = frozenset({
        NodeLog.ADDON_ADDED,
        NodeLog.ADDON_REMOVED
    })
    if action not in PERMITTED_GV_ACTIONS:
        logger.error(f"{action} is not permitted to be logged from GV")

    node_guid = node_url.split('/')[-1]
    user_guid = user_url.split('/')[-1]
    node = Node.objects.get(guids___id=node_guid)
    user = OSFUser.objects.get(guids___id=user_guid)
    node.add_log(
        action=action,
        auth=user,
        params={
            'node': node._id,
            'project': node.parent_id,
            'addon': addon
        }
    )
