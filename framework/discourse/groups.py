from .common import DiscourseException, request
from .users import get_username

from collections import Counter

def _create_group(project_node, should_save=True):
    data = {}
    data['name'] = project_node._id
    # We use this visible attribute to control the privacy of the project
    data['visible'] = 'true' if project_node.is_public else 'false'
    data['alias_level'] = '3'  # allows us to message this group directly
    try:
        result = request('post', '/admin/groups', data)
    except DiscourseException as e:
        if e.result.status_code == 422:
            # group already exists
            result = request('get', '/groups/' + str(project_node._id) + '.json')
        else:
            raise

    group_id = result['basic_group']['id']
    project_node.discourse_group_id = group_id
    project_node.discourse_group_public = project_node.is_public
    if should_save:
        project_node.save()

    return result

def create_group(project_node, should_save=True):
    result = _create_group(project_node, False)

    users = [get_username(user) for user in project_node.contributors if user.username]
    add_group_users(project_node, users, False)

    if should_save:
        project_node.save()

    return result

def get_or_create_group_id(project_node, should_save=True):
    if project_node.discourse_group_id is None:
        create_group(project_node, should_save)
    return project_node.discourse_group_id

def update_group_privacy(project_node, should_save=True):
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
    result = request('put', '/admin/groups/' + str(group_id), data)

    project_node.discourse_group_public = project_node.is_public
    project_node.discourse_view_only_keys = view_only_keys
    if should_save:
        project_node.save()

    return result

def add_group_users(project_node, users, should_save=True):
    group_id = get_or_create_group_id(project_node, False)
    data = {}
    data['usernames'] = ','.join(users)
    result = request('put', '/admin/groups/' + str(group_id) + '/owners.json', data)

    project_node.discourse_group_users = list((Counter(project_node.discourse_group_users) | Counter(users)).elements())
    if should_save:
        project_node.save()

    return result

def get_group_user_info(project_node, should_save=True):
    # we don't need the id, but need the group to exist
    get_or_create_group_id(project_node, False)
    result = request('get', '/groups/' + project_node._id + '/members.json')

    project_node.discourse_group_users = [user['username'] for user in result['owners']]
    if should_save:
        project_node.save()

    return result['owners']

def remove_group_users(project_node, users, should_save=True):
    group_id = get_or_create_group_id(project_node, False)
    group_users = get_group_user_info(project_node, False)
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
    update_group_privacy(project_node, False)

    users = [get_username(user) for user in project_node.contributors if user.username]
    users = [u for u in users if u]

    if project_node.discourse_group_users is None:
        get_group_user_info(project_node, False)

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
    group_id = project_node.discourse_group_id
    if group_id is None:
        return

    result = request('delete', '/admin/groups/' + str(group_id))
    project_node.discourse_group_id = None
    if should_save:
        project_node.save()
    return result
