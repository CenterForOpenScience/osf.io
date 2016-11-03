import common
# import here so they can all be imported through the module
from .comments import create_comment, edit_comment, delete_comment, undelete_comment  # noqa
from .common import DiscourseException, request  # noqa
from .groups import create_group, update_group_privacy, sync_group, delete_group  # noqa
from .topics import get_or_create_topic_id, sync_topic, delete_topic, undelete_topic  # noqa
from .users import get_username, get_user_apikey, logout  # noqa

def sync_project(project_node, should_save=True):
    """Sync project name, contributors, and visibility with Discourse creating project if necessary

    :param Node project_node: Project Node to sync on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if common.in_migration:
        return

    sync_group(project_node, False)
    sync_topic(project_node, False)

    if should_save:
        project_node.save()

def delete_project(project_node, should_save=True):
    """Delete project topics from Discourse. This makes them inaccessible,
    although the data is not actually lost and could later be restored.

    :param Node project_node: Project Node to delete on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if project_node.discourse_group_id is None or project_node.discourse_project_deleted:
        return

    request('delete', '/forum/' + project_node._id)
    project_node.discourse_project_deleted = True
    if should_save:
        project_node.save()

def undelete_project(project_node, should_save=True):
    """Reverse previous deletion of project topics from Discourse.

    :param Node project_node: Project Node to undelete on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if project_node.discourse_group_id is None or not project_node.discourse_project_deleted:
        return

    request('post', '/forum/' + project_node._id + '/restore')
    project_node.discourse_project_deleted = False
    if should_save:
        project_node.save()
