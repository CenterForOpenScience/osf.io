from framework.sessions import session
from framework.auth import User
import api.sso

from django.utils.text import slugify

import requests
import re
from furl import furl
import time

import ipdb

from website import settings

class DiscourseException(Exception):
    pass

def create_user(user):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/users/sync_sso')

    payload = {}
    payload['external_id'] = user._id
    payload['email'] = user.username
    payload['username'] = user.username
    payload['name'] = user.fullname
    payload['avatar_url'] = user.profile_image_url()

    url.args = api.sso.sign_payload(payload)
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.post(url.url)

    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to user create/sync request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['username']

def get_username(user=None):
    for_current_user = user is None
    if for_current_user:
        if 'auth_user_id' in session.data:
            user_id = session.data['auth_user_id']
            user = User.load(user_id)
        else:
            return None

    if user.discourse_username:
        return user.discourse_username

    url = furl(settings.DISCOURSE_SERVER_URL).join('/users/by-external/' + user._id + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code == 404:
        return create_user(user)
    elif result.status_code != 200:
        raise DiscourseException('Discourse server responded to user request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    username = result.json()['user']['username']

    user.discourse_username = username
    user.save()

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

def _get_embeddable_hosts():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/customize/embedding.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to getting embeddable hosts with '
                                 + str(result.status_code) + ' ' + result.text)
    return result.json()['embeddable_hosts']

def _config_embeddable_host():
    # just make sure one exists...
    embeddable_hosts = _get_embeddable_hosts()
    if len(embeddable_hosts):
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/embeddable_hosts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['embeddable_host[host]'] = settings.DOMAIN
    url.args['embeddable_host[category_id]'] = ''

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to setting embeddable host with '
                                 + str(result.status_code) + ' ' + result.text)

def _get_customizations():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/customize/css_html.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to getting customizations with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['site_customizations']

def _config_customization():
    old_ids = [c['id'] for c in _get_customizations()]
    for old_id in old_ids:
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_customizations/' + str(old_id))
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        result = requests.delete(url.url)
        if result.status_code != 204:
            raise DiscourseException('Discourse server responded to deleting customization with '
                                     + str(result.status_code) + ' ' + result.text)

    for customization in settings.DISCOURSE_SERVER_CUSTOMIZATIONS:
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_customizations')
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        for key, val in customization.items():
            url.args['site_customization[' + key + ']'] = val

        result = requests.post(url.url)
        if result.status_code != 201:
            raise DiscourseException('Discourse server responded to setting customization with '
                                     + str(result.status_code) + ' ' + result.text)
        time.sleep(0.1)

def configure_server_settings():
    for key, val in settings.DISCOURSE_SERVER_SETTINGS.items():
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_settings/' + key)
        url.args[key] = val
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        result = requests.put(url.url)
        if result.status_code != 200:
            raise DiscourseException('Discourse server responded to setting request with '
                                     + str(result.status_code) + ' ' + result.text)
        time.sleep(0.1)
    _config_embeddable_host()
    _config_customization()


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

    project_node.discourse_group_id = group_id
    project_node.save()

    return group_id

def get_or_create_group_id(project_node):
    group_id = project_node.discourse_group_id
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

    category_id = result.json()['category']['id']

    project_node.discourse_category_id = category_id
    project_node.save()

    return category_id

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

# returns containing project OR component node
def _get_project_node(node):
    try:
        return node.node
    except AttributeError:
        return node

def get_categories():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category info request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['category_list']['categories']

def get_or_create_category_id(project_node):
    category_id = project_node.discourse_category_id
    if category_id is not None:
        return category_id
    return create_category(project_node)

def delete_category(project_node):
    category_id = project_node.discourse_category_id
    if category_id is None:
        return

    topic_ids = [topic['id'] for topic in get_topics(project_node) if not topic['pinned']]
    for topic_id in topic_ids:
        delete_topic(topic_id)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/categories/' + str(category_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)

    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to category delete request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    project_node.discourse_category_id = None

def sync_project(project_node):
    sync_group(project_node)
    category_id = project_node.discourse_category_id
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

def _escape_markdown(text):
    r = re.compile(r'([\\`*_{}[\]()#+.!-])')
    return r.sub(r'\\\1', text)

def create_topic(node):
    project_node = _get_project_node(node)
    sync_project(project_node)

    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    # we can't do a more elegant isinstance check because that
    # causes import errors with circular referencing.
    try:
        node_type = 'wiki'
        node_title = 'Wiki page: ' + node.page_name
        node_description = 'the wiki page ' + _escape_markdown(node.page_name)
    except AttributeError:
        try:
            node_type = 'file'
            node_title = 'File: ' + node.name
            node_description = 'the file ' + _escape_markdown(node.name)
        except AttributeError:
                node_type = 'project'
                node_title = node.title
                node_description = _escape_markdown(node.title)

    #if isinstance(node, Node):
    #    node_title = node.title
    #elif isinstance(node, File):
    #    node_title = 'the file ' + node.name
    #elif isinstance(node, NodeWikiPage):
    #    node_title = 'the wiki page ' + node.page_name

    category_id = get_or_create_category_id(project_node)
    url.args['category'] = category_id
    url.args['title'] = node_title
    url.args['raw'] = 'This is the discussion topic for ' + node_description + '. What do you think about it?'

    if node_type == 'file':
        file_url = furl(settings.DOMAIN).join(node.get_persistant_guid()._id).url
        url.args['raw'] += '\nFile url: ' + file_url + '/'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic create request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    topic_id = result.json()['topic_id']

    node.discourse_topic_id = topic_id
    node.save()

    return topic_id

def get_or_create_topic_id(node):
    if node is None:
        return None

    # Dataverse files may have name=None at initialization
    # If this is the case, the topic can not be created yet
    #try:
    #    if node.name is None:
    #        return None
    #except AttributeError:
    #    pass

    topic_id = node.discourse_topic_id
    if topic_id:
        return topic_id
    return create_topic(node)

def get_topic(node):
    topic_id = node.discourse_topic_id

    url = furl(settings.DISCOURSE_SERVER_URL).join('/t/' + str(topic_id) + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic get request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)
    return result.json()

def delete_topic(node):
    topic_id = node.discourse_topic_id

    if topic_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/t/' + str(topic_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic delete request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    node.discourse_topic_id = None

def create_comment(node, comment_text, user=None, reply_to_post_number=None):
    if user is None or user == 'system':
        user_name = 'system'
    else:
        user_name = get_username(user)
        if user_name is None:
            raise DiscourseException('The user given does not exist in discourse!')

    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = user_name

    project_node = _get_project_node(node)
    category_id = get_or_create_category_id(project_node)

    topic_id = get_or_create_topic_id(node)
    url.args['category'] = category_id
    url.args['topic_id'] = topic_id
    url.args['raw'] = comment_text
    url.args['nested_post'] = 'true'
    if reply_to_post_number:
        url.args['reply_to_post_number'] = reply_to_post_number

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
