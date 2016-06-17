from .common import *
from .groups import *

from website import settings

import re
import requests.compat

# returns containing project OR component node
def _get_project_node(node):
    try:
        return node.node
    except AttributeError:
        return node

def get_topics(project_node):
    if project_node.is_public:
        return request('get', '/tags/' + project_node._id + '.json')
    else:
        username = get_username()
        return request('get', '/topics/private-messages-group/' + username + '/' + project_node._id + '.json')

def _escape_markdown(text):
    r = re.compile(r'([\\`*_{}[\]()#+.!-])')
    return r.sub(r'\\\1', text)

def _make_topic_content(node):
    node_title = {'wiki': 'Wiki page:', 'files': 'File: ', 'nodes': ''}[node.target_type]
    node_title += node.label
    node_description = {'wiki': 'the wiki page ', 'files': 'the file ', 'nodes': ''}[node.target_type]
    node_description += _escape_markdown(node.label)

    project_node = _get_project_node(node)

    topic_content = '`' + node_title + '`'
    topic_content += '\nThis is the discussion topic for ' + node_description + '.\n'
    topic_content += '\nContributors: ' + ', '.join(map(lambda c: c.display_full_name(), project_node.contributors))
    topic_content += '\nDate Created: ' + node.date_created.strftime("%Y-%m-%d %H:%M:%S")
    topic_content += '\nCategory: ' + project_node.category
    topic_content += '\nDescription: ' + (project_node.description if project_node.description else "No Description")
    topic_content += '\nLicense: ' + (project_node.license if project_node.license else "No License")

    if node.target_type == 'files':
        file_url = requests.compat.urljoin(settings.DOMAIN, node.guid_id)
        topic_content += '\nFile url: ' + file_url + '/'

    return topic_content

def _get_topic_tags(node):
    tags = [node.guid_id]#, node.guid_id + ':' + node.label]
    parent_node = _get_project_node(node)
    if parent_node is node:
        parent_node = node.parent_node
    while parent_node:
        tags.append(parent_node._id)
        #tags.append(parent_node._id + ':' + parent_node.label)
        parent_node = parent_node.parent_node

    return tags

def create_topic(node):
    data = {}
    # topics must be made private at first in order to correctly
    # address the project group. This can't be added in later.
    # But we can immediately convert to a public conversation after creation.
    data['archetype'] = 'private_message'

    project_node = _get_project_node(node)
    get_or_create_group_id(project_node) # insure existance of the group
    data['target_usernames'] = project_node._id
    data['title'] = node.guid_id
    data['raw'] = _make_topic_content(node)
    data['tags[]'] = _get_topic_tags(node)

    result = request('post', '/posts', data)

    node.discourse_topic_id = result['topic_id']
    node.discourse_topic_public = False
    node.discourse_post_id = result['id']
    node.save()

    if project_node.is_public:
        update_topic_privacy(node)

    return result

def update_topic_content(node):
    if node.discourse_post_id is None:
        return

    data = {}
    data['post[raw]'] = _make_topic_content(node)
    return request('put', '/posts/' + str(node.discourse_post_id), data)

def update_topic_privacy(node):
    if node.discourse_topic_id is None:
        return

    project_node = _get_project_node(node)
    if project_node.is_public == node.discourse_topic_public:
        return

    path = '/t/' + str(node.discourse_topic_id) + '/convert-topic'
    path += '/public' if project_node.is_public else '/private'
    result = request('put', path)

    node.discourse_topic_public = project_node.is_public
    node.save()

    return result

def update_topic_title_tags(node):
    data = {}
    data['title'] = node.guid_id
    data['tags[]'] = _get_topic_tags(node)
    return request('put', '/t/' + url.args['title'] + '/' + str(node.discourse_topic_id), data)

def get_or_create_topic_id(node):
    if node is None:
        return None
    if node.discourse_topic_id is None:
        create_topic(node)
    return node.discourse_topic_id

def get_topic(node):
    return request('get', '/t/' + str(node.discourse_topic_id) + '.json')

def delete_topic(node):
    if node.discourse_topic_id is None:
        return

    result = request('delete', '/t/' + str(node.discourse_topic_id) + '.json')

    node.discourse_topic_id = None
    node.discourse_post_id = None
    node.save()

    return result
