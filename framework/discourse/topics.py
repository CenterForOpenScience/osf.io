from . import *
from .groups import *

from website import settings

import re
import requests
from furl import furl

# returns containing project OR component node
def _get_project_node(node):
    try:
        return node.node
    except AttributeError:
        return node

def get_topics(project_node):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/tags/' + project_node._id + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to project topics get request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()

def _escape_markdown(text):
    r = re.compile(r'([\\`*_{}[\]()#+.!-])')
    return r.sub(r'\\\1', text)

def _create_or_update_topic_base_url(node):
    url = furl(settings.DISCOURSE_SERVER_URL)
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    # we can't do a more elegant isinstance check because that
    # causes import errors with circular referencing.
    try:
        node_type = 'wiki'
        node_guid = node._id
        node_title = 'Wiki page: ' + node.page_name
        node_description = 'the wiki page ' + _escape_markdown(node.page_name)
    except AttributeError:
        try:
            node_type = 'file'
            node_guid = node.get_guid()._id
            node_title = 'File: ' + node.name
            node_description = 'the file ' + _escape_markdown(node.name)
        except AttributeError:
                node_type = 'project'
                node_guid = node._id
                node_title = node.title
                node_description = _escape_markdown(node.title)

    project_node = _get_project_node(node)
    get_or_create_group_id(project_node) # insure existance of the group
    url.args['target_usernames'] = project_node._id

    url.args['title'] = node_guid
    url.args['raw'] = '`' + node_title + '` This is the discussion topic for ' + node_description + '. What do you think about it?'

    url.args['tags[]'] = node_guid
    parent_node = project_node
    if parent_node is node:
        parent_node = node.parent_node
    while parent_node:
        url.query.add('tags[]=' + str(parent_node._id))
        parent_node = parent_node.parent_node

    if node_type == 'file':
        file_url = furl(settings.DOMAIN).join(node_guid).url
        url.args['raw'] += '\nFile url: ' + file_url + '/'

    return url

def create_topic(node):
    url = _create_or_update_topic_base_url(node)
    url.path.add('/posts')

    # topics must be made private at first in order to correctly
    # address the project group. This can't be added in later.
    # But we can immediately convert to a private conversation after creation.
    url.args['archetype'] = 'private_message'

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic create request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    result_json = result.json()

    node.discourse_topic_id = result_json['topic_id']
    node.discourse_topic_public = False
    node.discourse_post_id = result_json['id']
    node.save()

    if _get_project_node(node).is_public:
        update_topic_privacy(node)

    return result_json

def update_topic_content(node):
    if node.discourse_post_id is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/posts/' + str(node.discourse_post_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['post[raw]'] = _create_or_update_topic_base_url(node).args['raw']

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic content update request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text[:500])

def update_topic_privacy(node):
    if node.discourse_topic_id is None:
        return

    project_node = _get_project_node(node)
    if project_node.is_public == node.discourse_topic_public:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/t/' + str(node.discourse_topic_id) + '/convert-topic')
    url.path.add('/public' if project_node.is_public else '/private')

    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic privacy update request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text[:500])

    node.discourse_topic_public = project_node.is_public
    node.save()

def update_topic_title_tags(node):
    url = _create_or_update_topic_base_url(node)
    url.path.add('/t/' + url.args['title'] + '/' + str(node.discourse_topic_id))

    result = requests.put(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to topic update request ' + result.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()

def get_or_create_topic_id(node):
    if node is None:
        return None
    if node.discourse_topic_id is None:
        create_topic(node)
    return node.discourse_topic_id

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
                                 + str(result.status_code) + ' ' + result.text[:500])

    node.discourse_topic_id = None
    node.discourse_post_id = None
