from .common import *
from .users import *

def _create_group(project_node):
    data = {}
    data['name'] = project_node._id
    data['visible'] = 'true' if project_node.is_public else 'false'
    data['alias_level'] = '3' # allows to message this group directly
    result = request('post', '/admin/groups', data)

    group_id = result['basic_group']['id']
    project_node.discourse_group_id = group_id
    project_node.save()

    return result

def create_group(project_node):
    result = _create_group(project_node)

    users = [get_username(user) for user in project_node.contributors if user.username]
    add_group_users(project_node, users)

    return result

def get_or_create_group_id(project_node):
    if project_node.discourse_group_id is None:
        create_group(project_node)
    return project_node.discourse_group_id

def update_group_visibility(project_node):
    group_id = project_node.discourse_group_id
    if group_id is None:
        return create_group(project_node)

    data = {}
    data['visible'] = 'true' if project_node.is_public else 'false'
    return request('put', '/admin/groups/' + str(group_id), data)

def add_group_users(project_node, users):
    group_id = get_or_create_group_id(project_node)
    data = {}
    data['usernames'] = ','.join(users)
    return request('put', '/admin/groups/' + str(group_id) + '/owners.json', data)

def get_group_users(project_node):
    # we don't need the id, but need the group to exist
    get_or_create_group_id(project_node)
    result = request('get', '/groups/' + project_node._id + '/members.json')
    return result['owners']

def remove_group_users(project_node, users):
    group_id = get_or_create_group_id(project_node)
    group_users = get_group_users(project_node)
    user_ids = [user['id'] for user in group_users if user['username'] in users]

    for user_id in user_ids:
        data = {}
        data['user_id'] = user_id
        request('delete', '/admin/groups/' + str(group_id) + '/members.json', data)

def sync_group(project_node):
    update_group_visibility(project_node)

    users = [get_username(user) for user in project_node.contributors if user.username]
    users = [u for u in users if u]
    current_users = [user['username'] for user in get_group_users(project_node)]

    users_to_add = [u for u in users if u not in current_users]
    if users_to_add:
        add_group_users(project_node, users_to_add)

    users_to_remove = [u for u in current_users if u not in users]
    if users_to_remove:
        remove_group_users(project_node, users_to_remove)

def delete_group(project_node):
    group_id = project_node.discourse_group_id
    if group_id is None:
        return

    result = request('delete', '/admin/groups/' + str(group_id))
    project_node.discourse_group_id = None
    project_node.save()
    return result
