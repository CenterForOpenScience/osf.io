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
    return request('get', '/projects/' + project_node._id + '.json')
    #if project_node.is_public:
    #    return request('get', '/tags/' + project_node._id + '.json')
    #else:
    #    username = get_username()
    #    return request('get', '/topics/private-messages-group/' + username + '/' + project_node._id + '.json')

def _escape_markdown(text):
    r = re.compile(r'([\\`*_{}[\]()#+.!-])')
    return r.sub(r'\\\1', text)

def _make_topic_content(node):
    node_title = {'wiki': 'Wiki page:', 'files': 'File: ', 'nodes': ''}[node.target_type]
    node_title += node.label
    node_description = {'wiki': 'the wiki page ', 'files': 'the file ', 'nodes': ''}[node.target_type]
    node_description += _escape_markdown(node.label)

    project_node = _get_project_node(node)

    topic_content = ''#'`' + node_title + '`'
    topic_content += '\nThis is the discussion topic for ' + node_description + '.\n'
    topic_content += '\nContributors: ' + ', '.join(map(lambda c: c.display_full_name(), project_node.contributors))
    #topic_content += '\nDate Created: ' + node.date_created.strftime("%Y-%m-%d %H:%M:%S")
    topic_content += '\nCategory: ' + project_node.category
    topic_content += '\nDescription: ' + (project_node.description if project_node.description else "No Description")
    topic_content += '\nLicense: ' + (project_node.license if project_node.license else "No License")

    if node.target_type == 'files':
        file_url = requests.compat.urljoin(settings.DOMAIN, node.guid_id)
        topic_content += '\nFile url: ' + file_url + '/'

    return topic_content

def _get_parent_guids(node):
    parent_guids = []
    parent_node = _get_project_node(node)
    while parent_node:
        parent_guids.append(parent_node._id)
        #tags.append(parent_node._id + ':' + parent_node.label)
        parent_node = parent_node.parent_node

    return parent_guids

def create_topic(node):
    data = {}
    project_node = _get_project_node(node)

    # privacy is completely relegated to the group with the corresponding project_guid
    data['archetype'] = 'regular'

    get_or_create_group_id(project_node) # insure existance of the group
    #data['target_usernames'] = project_node._id
    data['title'] = node.label
    data['raw'] = _make_topic_content(node)
    data['parent_guids[]'] = _get_parent_guids(node)
    data['topic_guid'] = node.guid_id

    result = request('post', '/posts', data)

    node.discourse_topic_id = result['topic_id']
    node.discourse_topic_public = False
    node.discourse_post_id = result['id']
    node.save()

    return result

def update_topic_content(node):
    if node.discourse_post_id is None:
        return

    data = {}
    data['post[raw]'] = _make_topic_content(node)
    return request('put', '/posts/' + str(node.discourse_post_id), data)

def update_topic_title(node):
    if node.discourse_topic_id is None:
        return

    data = {}
    data['title'] = node.label
    data['parent_guids[]'] = _get_parent_guids(node)
    return request('put', '/t/' + node.guid_id + '/' + str(node.discourse_topic_id), data)

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
