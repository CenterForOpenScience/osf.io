from . import *
from .users import *

from website import settings

import requests
from furl import furl

def create_group(project_node):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_node._id
    url.args['visible'] = 'true' if project_node.is_public else 'false'
    url.args['alias_level'] = '3' # allows to message this group directly

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group creation request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    group_id = result.json()['basic_group']['id']

    project_node.discourse_group_id = group_id
    project_node.save()

    return result.json()

def get_or_create_group_id(project_node):
    if project_node.discourse_group_id is None:
        sync_group(project_node)
    return project_node.discourse_group_id

def update_group_visibility(project_node):
    group_id = project_node.discourse_group_id
    if group_id is None:
        create_group(project_node)
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['visible'] = 'true' if project_node.is_public else 'false'

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group change request with '
                                 + str(result.status_code) + ' ' + result.text)

def add_group_users(project_node, users):
    group_id = get_or_create_group_id(project_node)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id) + '/owners.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['usernames'] = ','.join(users)

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group add user request with '
                                 + str(result.status_code) + ' ' + result.text)

def get_group_users(project_node):
    # we don't need the id, but need the group to exist
    get_or_create_group_id(project_node)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/groups/' + project_node._id + '/members.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group get users request with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['owners']

def remove_group_users(project_node, users):
    group_id = get_or_create_group_id(project_node)
    group_users = get_group_users(project_node)
    user_ids = [user['id'] for user in group_users if user['username'] in users]

    for user_id in user_ids:
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id) + '/members.json')
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        url.args['user_id'] = user_id

        result = requests.delete(url.url)
        if result.status_code != 200:
            raise DiscourseException('Discourse server responded to group remove user request with '
                                     + str(result.status_code) + ' ' + result.text)

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

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group delete request with '
                                 + str(result.status_code) + ' ' + result.text)

    project_node.discourse_group_id = None
