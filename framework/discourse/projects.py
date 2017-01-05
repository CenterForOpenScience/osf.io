import framework.discourse.common
import framework.discourse.topics
from framework.discourse import common, users

def sync_project_details(project_node, should_save=True):
    """If the project's public-ness, view-only keys, or contributors have changed, sync these

    :param Node project_node: Project Node that should be updated in Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    view_only_keys = [a.key for a in project_node.private_links_active if not a.anonymous]

    contributors = [users.get_discourse_username(osf_user) for osf_user in project_node.contributors if osf_user.username]

    # check if there are any changes that need a resync.
    # note that
    if (project_node.discourse_project_created and
            project_node.discourse_project_public == project_node.is_public and
            project_node.discourse_view_only_keys == view_only_keys and
            project_node.discourse_project_contributors == contributors):
        return

    data = {
        'is_public': 'true' if project_node.is_public else 'false',
        'view_only_keys[]': view_only_keys,
        'contributors': ','.join(contributors)
    }
    common.request('put', '/forum/' + str(project_node._id), data)

    project_node.discourse_project_created = True
    project_node.discourse_project_public = project_node.is_public
    project_node.discourse_view_only_keys = view_only_keys
    project_node.discourse_project_contributors = contributors

    if should_save:
        project_node.save()

def sync_project(project_node, should_save=True):
    """Sync project name, contributors, and visibility with Discourse creating project if necessary

    :param Node project_node: Project Node to sync on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if common.in_migration:
        return

    try:
        sync_project_details(project_node, False)
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error syncing a project, check your Discourse server')
        return

    framework.discourse.topics.sync_topic(project_node, False)

    if project_node.discourse_project_deleted and not project_node.is_deleted:
        undelete_project(project_node, False)
    elif not project_node.discourse_project_deleted and project_node.is_deleted:
        delete_project(project_node, False)

    if should_save:
        project_node.save()

def get_project(project_node, user=None, view_only=None):
    """ Get the first page of the latest topics in the project

    :param Node project_node: Project Node to query on Discourse
    :param User user: The user to request the project as, or None for admin access
    """
    data = {}
    if view_only:
        data['view_only'] = view_only
    username = 'system'
    if user:
        username = users.get_discourse_username(user)
    return common.request('get', '/forum/' + str(project_node._id) + '.json', data, username=username)['topic_list']

def delete_project(project_node, should_save=True):
    """Delete project topics from Discourse. This makes them inaccessible,
    although the data is not actually lost and could later be restored.
    A project cannot be deleted if a parent node has already been deleted.
    In that case, this does nothing.

    :param Node project_node: Project Node to delete on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    if not project_node.discourse_project_created or framework.discourse.topics.some_parent_is_deleted(project_node):
        return

    try:
        common.request('delete', '/forum/' + project_node._id)
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error deleting a project, check your Discourse server')
        return

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

    try:
        sync_project_details(project_node, False)
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error undeleting a project, check your Discourse server')
        return

    project_node.discourse_project_deleted = False
    if should_save:
        project_node.save()
