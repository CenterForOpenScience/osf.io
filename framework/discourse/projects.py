import framework.discourse.common
import framework.discourse.topics
from framework.discourse.common import request
from framework.discourse.users import get_username

def _sync_project(project_node):
    """If the project's public-ness, view-only keys, or contributors have changed, sync these

    :param Node project_node: Project Node that should be updated in Discourse
    """
    view_only_keys = [a.key for a in project_node.private_links_active if not a.anonymous]

    contributors = [get_username(user) for user in project_node.contributors if user.username]
    contributors = [c for c in contributors if c]

    if (project_node.discourse_project_created and
            project_node.discourse_project_public == project_node.is_public and
            len(set(project_node.discourse_view_only_keys) ^ set(view_only_keys)) == 0 and
            len(set(project_node.discourse_project_contributors) ^ set(contributors)) == 0):
        return

    data = {}
    data['is_public'] = 'true' if project_node.is_public else 'false'
    data['view_only_keys[]'] = view_only_keys
    data['contributors'] = ','.join(contributors)
    request('put', '/forum/' + str(project_node._id), data)

    project_node.discourse_project_created = True
    project_node.discourse_project_public = project_node.is_public
    project_node.discourse_view_only_keys = view_only_keys
    project_node.discourse_project_contributors = contributors

def sync_project(project_node, should_save=True):
    """Sync project name, contributors, and visibility with Discourse creating project if necessary

    :param Node project_node: Project Node to sync on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if framework.discourse.common.in_migration:
        return

    _sync_project(project_node)

    framework.discourse.topics.sync_topic(project_node, False)

    if project_node.discourse_project_deleted and not project_node.is_deleted:
        undelete_project(project_node, False)
    elif not project_node.discourse_project_deleted and project_node.is_deleted:
        delete_project(project_node, True)

    if should_save:
        project_node.save()

def get_project(project_node, user=None, view_only=None):
    """ Get the first page of the latest topics in the project

    :param Node projecT_node: Project Node to query on Discourse
    :param User user: The user to request the project as, or None for admin access
    """
    data = {}
    if view_only:
        data['view_only'] = view_only
    username = get_username(user)
    return request('get', '/forum/' + str(project_node._id) + '.json', data, username=username)['topic_list']

def delete_project(project_node, should_save=True):
    """Delete project topics from Discourse. This makes them inaccessible,
    although the data is not actually lost and could later be restored.

    :param Node project_node: Project Node to delete on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if not project_node.discourse_project_created or project_node.discourse_project_deleted:
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
    if not project_node.discourse_project_created or not project_node.discourse_project_deleted:
        return
    # force resync of project
    project_node.discourse_project_created = False
    _sync_project(project_node)

    project_node.discourse_project_deleted = False
    if should_save:
        project_node.save()
