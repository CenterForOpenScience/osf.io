from framework.sessions import session
from django.utils.text import slugify

import requests
from furl import furl
import json

from website import settings

class DiscourseException(Exception):
    pass

def get_username(user_id=None):
    for_current_user = user_id is None
    if for_current_user:
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

    if for_current_user:
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

def create_group(project_node):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_node._id
    url.args['visible'] = 'true' if project_node.is_public else 'false'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group creation request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    group_id = result.json()['basic_group']['id']
    return group_id

def get_group_id(project_node):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group information request with '
                                 + str(result.status_code) + ' ' + result.text)

    group_ids = [group['id'] for group in result.json() if group['name'] == project_node._id]
    if group_ids:
        return group_ids[0]
    return None

def get_or_create_group_id(project_node):
    group_id = get_group_id(project_node)
    if group_id is not None:
        return group_id
    return create_group(project_node)

def update_group_visibility(project_node):
    group_id = get_or_create_group_id(project_node)

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

    users = [get_username(user._id) for user in project_node.contributors]
    current_users = [user['username'] for user in get_group_users(project_node)]

    users_to_add = [u for u in users if u not in current_users]
    if users_to_add:
        add_group_users(project_node, users_to_add)

    users_to_remove = [u for u in current_users if u not in users]
    if users_to_remove:
        remove_group_users(project_node, users_to_remove)

def delete_group(project_node):
    group_id = get_group_id(project_node)
    if group_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/groups/' + str(group_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to group delete request with '
                                 + str(result.status_code) + ' ' + result.text)

def create_category(project_node):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_node.title + ' / ' + project_node._id
    url.args['slug'] = slugify(project_node.title + '-' + project_node._id)
    url.args['color'] = 'AB9364'
    url.args['text_color'] = 'FFFFFF'
    url.args['allow_badges'] = 'true'

    # ensure group exists
    get_or_create_group_id(project_node)
    url.args['permissions[' + project_node._id + ']'] = '1'
    if project_node.is_public:
        url.args['permissions[everyone]'] = '2'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category create request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['category']['id']

def update_category(project_node, category_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories/' + str(category_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['name'] = project_node.title + ' / ' + project_node._id
    url.args['slug'] = slugify(project_node.title + '-' + project_node._id)
    url.args['color'] = 'AB9364'
    url.args['text_color'] = 'FFFFFF'
    url.args['allow_badges'] = 'true'

    # ensure group exists
    get_or_create_group_id(project_node)
    url.args['permissions[' + project_node._id + ']'] = '1'
    if project_node.is_public:
        url.args['permissions[everyone]'] = '2'

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category update request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def get_categories():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category info request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['category_list']['categories']

def get_category_id(project_node):
    categories = get_categories()
    ids = [category['id'] for category in categories if category['slug'].endswith('-' + project_node._id)]
    if ids:
        return ids[0]
    return None

def get_or_create_category_id(project_node):
    category_id = get_category_id(project_node)
    if category_id is not None:
        return category_id
    return create_category(project_node)

def delete_category(project_node):
    category_id = get_category_id(project_node)
    if category_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories/' + str(category_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category delete request with '
                                 + str(result.status_code) + ' ' + result.text)

def sync_project(project_node):
    sync_group(project_node)
    category_id = get_category_id(project_node)
    if category_id is None:
        create_category(project_node)
    else:
        update_category(project_node, category_id)

def delete_project(project_node):
    delete_category(project_node)
    delete_group(project_node)

def get_topics(project_node):
    sync_project(project_node)

    category_slug = slugify(project_node.title + '-' + project_node._id)
    url = furl(settings.DISCOURSE_SERVER_URL).join('/c/' + category_slug + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic get request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['topic_list']['topics']

def create_topic(project_node, file_node):
    sync_project(project_node)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    category_id = get_or_create_category_id(project_node)
    url.args['category'] = category_id
    url.args['title'] = 'File: ' + file_node.name + ' (' + file_node._id + ')'
    url.args['raw'] = 'The file ' + file_node.name + ' has been uploaded. What do you think about it?'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic create request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['topic_id']

def get_topic_id(project_node, file_node):
    topics = get_topics(project_node)
    ids = [topic['id'] for topic in topics if topic['title'].endswith('(' + file_node._id + ')')]
    if ids:
        return ids[0]
    return None

def get_or_create_topic_id(project_node, file_node):
    topic_id = get_topic_id(project_node, file_node)
    if topic_id:
        return topic_id
    return create_topic(project_node, file_node)

def get_topic(project_node, file_node):
    topic_id = get_or_create_topic_id(project_node, file_node)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/t/' + str(topic_id) + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic get request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)
    return result.json()

def delete_topic(project_node, file_node):
    topic_id = get_topic_id(project_node, file_node)
    if topic_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/t/' + str(topic_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic delete request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def create_comment(project_node, file_node, comment_text):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    category_id = get_or_create_category_id(project_node)
    topic_id = get_or_create_topic_id(project_node, file_node)
    url.args['category'] = category_id
    url.args['topic_id'] = topic_id
    url.args['raw'] = comment_text
    url.args['nested_post'] = 'true'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment create request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['post']['id']

def edit_comment(comment_id, comment_text):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(comment_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['post[raw]'] = comment_text

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment edit request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def delete_comment(comment_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(comment_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment delete request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

def undelete_comment(comment_id):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(comment_id) + '/recover')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to comment undelete request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)
