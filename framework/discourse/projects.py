import logging

import framework.discourse.common
import framework.discourse.topics
from framework.discourse import common, users

import requests

logger = logging.getLogger(__name__)

def sync_project_details(project_node, should_save=True):
    """If the project's public-ness, view-only keys, or contributors have changed, sync these

    :param Node project_node: Project Node that should be updated in Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    view_only_keys = [a.key for a in project_node.private_links_active if not a.anonymous]

    contributors = [users.get_discourse_username(osf_user) for osf_user in project_node.contributors if osf_user.username]
    contributors = [c for c in contributors if c]

    # check if there are any changes that need a resync.
    # we check the difference of the lists because migrations might report
    # the lists back in different orders
    if (project_node.discourse_project_created and
            project_node.discourse_project_public == project_node.is_public and
            len(set(project_node.discourse_view_only_keys) ^ set(view_only_keys)) == 0 and
            len(set(project_node.discourse_project_contributors) ^ set(contributors)) == 0):
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
    """Sync project name, contributors, visibility, and deletion status with Discourse, creating project if necessary

    :param Node project_node: Project Node to sync on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    :return bool: True if the function finished without internal errors
    """
    if common.in_migration:
        return True

    try:
        sync_project_details(project_node, False)
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error syncing a project, check your Discourse server')
        return False

    if not framework.discourse.topics.sync_topic(project_node, False):
        return False

    if project_node.discourse_project_deleted and not project_node.is_deleted:
        if not undelete_project(project_node, False):
            return False
    elif not project_node.discourse_project_deleted and project_node.is_deleted:
        if not delete_project(project_node, False):
            return False

    if should_save:
        project_node.save()

    return True

def get_project(project_node, user=None, view_only=None):
    """ Get the first page of the latest topics in the project

    :param Node project_node: Project Node to query on Discourse
    :param User user: The user to request the project as, or None for admin access
    :return json: the json containing the latest project topics, or None if retrieval failed
    """
    data = {}
    if view_only:
        data['view_only'] = view_only
    username = 'system'
    if user:
        username = users.get_discourse_username(user)

    try:
        return common.request('get', '/forum/' + str(project_node._id) + '.json', data, username=username)['topic_list']
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error getting latest topics, check your Discourse server')
        return None

def delete_project(project_node, should_save=True):
    """Delete project topics from Discourse. This makes them inaccessible,
    although the data is not actually lost and could later be restored.
    A project cannot be deleted if a parent node has already been deleted.
    In that case, this does nothing.

    :param Node project_node: Project Node to delete on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    :return bool: True if the function finished without internal errors
    """
    if not project_node.discourse_project_created or framework.discourse.topics.some_parent_is_deleted(project_node):
        return True

    # Prevent inconsistancy -- or the callback on save() will undelete the project
    if not project_node.is_deleted:
        project_node.is_deleted = True

    try:
        common.request('delete', '/forum/' + project_node._id)
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error deleting a project, check your Discourse server')
        return False

    project_node.discourse_project_deleted = True
    if should_save:
        project_node.save()

    return True

def undelete_project(project_node, should_save=True):
    """Reverse previous deletion of project topics from Discourse.

    :param Node project_node: Project Node to undelete on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    :return bool: True if the function finished without internal errors
    """
    if not project_node.discourse_project_created or not project_node.discourse_project_deleted:
        return True

    # Prevent inconsistancy -- or the callback on save() will delete the project
    if project_node.is_deleted:
        project_node.is_deleted = False

    # force resync of project
    project_node.discourse_project_created = False

    try:
        sync_project_details(project_node, False)
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error undeleting a project, check your Discourse server')
        return False

    project_node.discourse_project_deleted = False
    if should_save:
        project_node.save

    return True
