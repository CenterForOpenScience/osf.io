import common
# import here so they can all be imported through the module
from .comments import create_comment, edit_comment, delete_comment, undelete_comment  # noqa
from .common import DiscourseException, request  # noqa
from .groups import create_group, update_group_privacy, sync_group, delete_group  # noqa
from .topics import get_or_create_topic_id, create_topic, sync_topic, delete_topic, undelete_topic  # noqa
from .users import get_username, get_user_apikey, logout  # noqa

def sync_project(project_node, should_save=True):
    if common.in_migration:
        return

    sync_group(project_node, False)

    if project_node.discourse_topic_id:
        sync_topic(project_node, False)
    else:
        create_topic(project_node, False)

    if should_save:
        project_node.save()

def delete_project(project_node, should_save=True):
    delete_group(project_node, should_save)
