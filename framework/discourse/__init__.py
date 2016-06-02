from framework.sessions import session

import requests
from furl import furl

from website import settings

class DiscourseException(Exception):
    pass

def get_username(user_id=None):
    if not user_id:
        if 'auth_discourse_username' in session.data:
            return session.data['auth_discourse_username']

        if 'auth_user_id' in session.data:
            user_id = session.data['auth_user_id']
        else:
            return None

    url = furl(settings.DISCOURSE_SERVER_URL).join('/users/by-external/' + user_id + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to user request with '
                                 + str(result.status_code) + ' ' + result.text)

    username = result.json()['user']['username']
    session.data['auth_discourse_username'] = username

    return username

def logout():
    username = get_username()
    if username is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/session/' + username)
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = username

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to logout request with '
                                 + str(result.status_code) + ' ' + result.text)

def configure_server_settings():
    discourse_settings = settings.DISCOURSE_SERVER_SETTINGS
    for key, val in settings.DISCOURSE_SERVER_SETTINGS.items():
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_settings/' + key)
        url.args[key] = val
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        result = requests.put(url.url)
        if result.status_code != 200:
            raise DiscourseException('Discourse server responded to setting request with '
                                     + str(result.status_code) + ' ' + result.text)

def create_group(project_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_id
    url.args['visible'] = 'false'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group creation request with '
                                 + str(result.status_code) + ' ' + result.text)

    group_id = result.json()['basic_group']['id']
    return group_id

def get_group_id(project_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group information request with '
                                 + str(result.status_code) + ' ' + result.text)

    group_ids = [group['id'] for group in result.json() if group['name'] == project_id]
    if group_ids:
        return group_ids[0]
    return None

def get_or_create_group_id(project_id):
    group_id = get_group_id(project_id)
    if group_id is not None:
        return group_id
    return create_group(project_id)

def set_group_visibility(project_id, visible):
    group_id = get_or_create_group_id(project_id)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['visible'] = 'true' if visible else 'false'

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group change request with '
                                 + str(result.status_code) + ' ' + result.text)

def add_group_users(project_id, users):
    group_id = get_or_create_group_id(project_id)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id) + '/owners.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['usernames'] = ','.join(users)

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group add user request with '
                                 + str(result.status_code) + ' ' + result.text)

def get_group_users(project_id):
    # we don't need the id, but need the group to exist
    get_or_create_group_id(project_id)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/groups/' + project_id + '/members.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group get users request with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['owners']

def remove_group_users(project_id, users):
    group_id = get_or_create_group_id(project_id)
    group_users = get_group_users(project_id)
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

def sync_group_users(project_id, users):
    current_users = [user['username'] for user in get_group_users(project_id)]
    users_to_add = [u for u in users if u not in current_users]
    if users_to_add:
        add_group_users(project_id, users_to_add)

    users_to_remove = [u for u in current_users if u not in users]
    if users_to_remove:
        remove_group_users(project_id, users_to_remove)

def delete_group(project_id):
    group_id = get_group_id(project_id)
    if group_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group delete request with '
                                 + str(result.status_code) + ' ' + result.text)

def local_group_test():
    project_id = 'foobar123'
    sync_group_users(project_id, [])
    assert len(get_group_users(project_id)) == 0

    sync_group_users(project_id, ['acshikh', 'acshikh1'])
    assert len(get_group_users(project_id)) == 2

    sync_group_users(project_id, ['acshikh'])
    assert len(get_group_users(project_id)) == 1

    sync_group_users(project_id, ['acshikh', 'acshikh1'])
    assert len(get_group_users(project_id)) == 2

    sync_group_users(project_id, [])
    assert len(get_group_users(project_id)) == 0

    delete_group(project_id)
    assert get_group_id(project_id) is None

    print('test passed')

def create_category(project_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_id
    url.args['color'] = 'AB9364'
    url.args['text_color'] = 'FFFFFF'
    url.args['allow_badges'] = 'true'

    # ensure group exists
    get_or_create_group_id(project_id)
    url.args['permissions[' + project_id + ']'] = '1'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category creation request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['category']['id']

def get_categories():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category info request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['category_list']['categories']

def get_category_id(project_id):
    categories = get_categories()
    ids = [category['id'] for category in categories if category['name'] == project_id]
    if ids:
        return ids[0]
    return None

def get_or_create_category_id(project_id):
    category_id = get_category_id(project_id)
    if category_id is not None:
        return category_id
    return create_category(project_id)

def set_category_publicity(project_id, is_public):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories/' + str(get_or_create_category_id(project_id)))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_id
    url.args['color'] = 'AB9364'
    url.args['text_color'] = 'FFFFFF'
    url.args['allow_badges'] = 'true'

    # ensure group exists
    get_or_create_group_id(project_id)
    url.args['permissions[' + project_id + ']'] = '1'
    if is_public:
        url.args['permissions[everyone]'] = '2'

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category change request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def delete_category(project_id):
    category_id = get_category_id(project_id)
    if category_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories/' + str(category_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category delete request with '
                                 + str(result.status_code) + ' ' + result.text)

def local_category_test():
    project_id = 'foobar123'

    set_category_publicity(project_id, True)

    delete_category(project_id)
    assert get_category_id(project_id) is None

    print('test passed')

def sync_project(project_id):
    pass

def delete_project(project_id):
    delete_category(project_id)
    delete_group(project_id)
