from .common import DiscourseException, request
from .users import get_username

from collections import Counter

def _create_group(project_node, should_save=True):
    """Create a group for the project node, using the guid as the group name,
    and also carrying over is_public and view_only_keys to the group.

    :param Node project_node: Project Node to create a group for on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    :param int: the group ID of the group created
    """
    view_only_keys = [a.key for a in project_node.private_links_active if not a.anonymous]

    data = {}
    data['name'] = project_node._id
    # We use this visible attribute to control the privacy of the project
    data['visible'] = 'true' if project_node.is_public else 'false'
    data['view_only_keys[]'] = view_only_keys
    data['alias_level'] = '3'  # allows us to message this group directly
    try:
        result = request('post', '/admin/groups', data)
    except DiscourseException as e:
        if e.result.status_code == 422:
            # group already exists
            result = request('get', '/groups/' + str(project_node._id) + '.json')
            # we can't know what view only keys have been set on it, though.
            # so don't let that value update on the node.
            view_only_keys = project_node.discourse_view_only_keys
        else:
            raise

    group_id = result['basic_group']['id']
    project_node.discourse_group_id = group_id
    project_node.discourse_group_public = result['basic_group']['visible']
    project_node.discourse_view_only_keys = view_only_keys
    if should_save:
        project_node.save()

    return group_id

def create_group(project_node, should_save=True):
    """Create a group for the project node, using the guid as the group name,
    carrying over whether the project is public, and adding the contributors
    of the project as users in the group.

    :param Node project_node: Project Node to create a group for on Discourse
    :param bool should_save: Whether the function should call project_node.save()
    :return int: the group ID of the group created
    """
    group_id = _create_group(project_node, False)

    users = [get_username(user) for user in project_node.contributors if user.username]
    add_group_users(project_node, users, False)

    if should_save:
        project_node.save()

    return group_id

def get_or_create_group_id(project_node, should_save=True):
    """Return the Discourse group ID for this project, calling create_group if necessary.

    :param Node project_node: Project Node to find the group ID for
    :param bool should_save: Whether the function should call project_node.save() if creating the group
    :return int: the group ID
    """
    if project_node.discourse_group_id is None:
        return create_group(project_node, should_save)
    return project_node.discourse_group_id

def update_group_privacy(project_node, should_save=True):
    """If the project's public-ness or view-only keys have changed, sync these to the group

    :param Node project_node: Project Node whose group should be updated in Discourse
    :param bool should_save: Whether the function should call project_node.save() after making changes
    """
    group_id = project_node.discourse_group_id
    if group_id is None:
        return create_group(project_node, False)

    view_only_keys = [a.key for a in project_node.private_links_active if not a.anonymous]

    if (project_node.discourse_group_public == project_node.is_public and
       len(set(project_node.discourse_view_only_keys) ^ set(view_only_keys)) == 0):
        return

    data = {}
    data['visible'] = 'true' if project_node.is_public else 'false'
    data['view_only_keys[]'] = view_only_keys
    request('put', '/admin/groups/' + str(group_id), data)

    project_node.discourse_group_public = project_node.is_public
    project_node.discourse_view_only_keys = view_only_keys
    if should_save:
        project_node.save()

def add_group_users(project_node, users, should_save=True):
    """Add the given users (by guids) to the project's group

    :param Node project_node: Project Node whose group should be updated in Discourse
    :param string[] users: The GUIDS of users to add to the group
    :param bool should_save: Whether the function should call project_node.save()
    """
    group_id = get_or_create_group_id(project_node, False)
    data = {}
    data['usernames'] = ','.join(users)
    request('put', '/admin/groups/' + str(group_id) + '/owners.json', data)

    project_node.discourse_group_users = list((Counter(project_node.discourse_group_users) | Counter(users)).elements())
    if should_save:
        project_node.save()

def retrieve_group_user_info(project_node, should_save=True):
    """Request and return the owner list of the group, with user attributes
    Place the list of just the GUIDs into project_node.discourse_group_users

    :param Node project_node: Project Node whose group should queried in Discourse
    :param bool should_save: Whether the function should call project_node.save()
    after caching usernames in project_node
    :return list: list of the owners as dictionaries with attributes
    """
    # we don't need the id, but need the group to exist
    get_or_create_group_id(project_node, False)
    result = request('get', '/groups/' + project_node._id + '/members.json')

    project_node.discourse_group_users = [user['username'] for user in result['owners']]
    if should_save:
        project_node.save()

    return result['owners']

def remove_group_users(project_node, users, should_save=True):
    """Remove the given users (by guids) to the project's group

    :param Node project_node: Project Node whose group should be updated in Discourse
    :param list users: The GUIDS of users to remove from the group
    :param bool should_save: Whether the function should call project_node.save()
    """
    group_id = get_or_create_group_id(project_node, False)
    group_users = retrieve_group_user_info(project_node, False)
    user_ids = [user['id'] for user in group_users if user['username'] in users]

    try:
        for i, user_id in enumerate(user_ids):
            data = {}
            data['user_id'] = user_id
            request('delete', '/admin/groups/' + str(group_id) + '/members.json', data)
            project_node.discourse_group_users.remove(users[i])
    finally:
        if should_save:
            project_node.save()

def sync_group(project_node, should_save=True):
    """Sync group privacy and users in Discourse. Does nothing if no changes need to be made.

    :param Node project_node: Project Node whose group should be updated in Discourse
    :param bool should_save: Whether the function should call project_node.save() if changes are made
    """
    update_group_privacy(project_node, False)

    users = [get_username(user) for user in project_node.contributors if user.username]
    users = [u for u in users if u]

    if project_node.discourse_group_users is None:
        retrieve_group_user_info(project_node, False)

    current_users = project_node.discourse_group_users

    users_to_add = list((Counter(users) - Counter(current_users)).elements())
    if users_to_add:
        add_group_users(project_node, users_to_add, False)

    users_to_remove = list((Counter(current_users) - Counter(users)).elements())
    if users_to_remove:
        remove_group_users(project_node, users_to_remove, False)

    if should_save:
        project_node.save()

def delete_group(project_node, should_save=True):
    """Delete group in Discourse.

    :param Node project_node: Project Node whose group should be deleted in Discourse
    :param bool should_save: Whether the function should call project_node.save()
    """
    group_id = project_node.discourse_group_id
    if group_id is None:
        return

    request('delete', '/admin/groups/' + str(group_id))
    project_node.discourse_group_id = None
    if should_save:
        project_node.save()
