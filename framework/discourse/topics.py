import common
from .common import DiscourseException, request
from .categories import file_category, wiki_category, project_category
from .groups import get_or_create_group_id

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
    return request('get', '/forum/' + project_node._id + '.json')

def _escape_markdown(text):
    r = re.compile(r'([\\`*_{}[\]()#+.!-])')
    return r.sub(r'\\\1', text)

def make_topic_content(node):
    node_title = {'wiki': 'Wiki page:', 'files': 'File: ', 'nodes': ''}[node.target_type]
    node_title += node.label
    node_description = {'wiki': 'the wiki page ', 'files': 'the file ', 'nodes': ''}[node.target_type]
    node_description += _escape_markdown(node.label)

    project_node = _get_project_node(node)
    topic_content = 'This is the discussion topic for ' + node_description + '.'
    topic_content += '\nRelevant contributors: ' + ', '.join([c.display_full_name() for c in project_node.contributors[:6]])
    if len(project_node.contributors) > 6:
        topic_content += '...'

    if node.target_type == 'files':
        file_url = requests.compat.urljoin(settings.DOMAIN, node.guid_id)
        topic_content += '\nFile url: ' + file_url

    return topic_content

def get_parent_guids(node):
    parent_guids = []
    parent_node = _get_project_node(node)
    while parent_node:
        parent_guids.append(parent_node._id)
        parent_node = parent_node.parent_node

    return parent_guids

# Safe to call multiple times, but will make a new topic each time!
def create_topic(node):
    data = {}
    project_node = _get_project_node(node)

    if wiki_category is None:
        raise DiscourseException('Cannot create topic. Discourse did not properly load when the OSF was started. Ensure Discourse is running and restart the OSF.')

    # privacy is completely relegated to the group with the corresponding project_guid
    data['archetype'] = 'regular'

    get_or_create_group_id(project_node)  # ensure existance of the group
    data['title'] = node.label
    data['raw'] = make_topic_content(node)
    data['parent_guids[]'] = get_parent_guids(node)
    data['topic_guid'] = node.guid_id
    data['category'] = {'wiki': wiki_category, 'files': file_category, 'nodes': project_category}[node.target_type]

    result = request('post', '/posts', data)

    node.discourse_topic_id = result['topic_id']
    node.discourse_topic_title = data['title']
    node.discourse_topic_parent_guids = data['parent_guids[]']
    node.discourse_post_id = result['id']
    node.save()

    return result

def _update_topic_content(node):
    if node.discourse_post_id is None:
        return

    data = {}
    data['post[raw]'] = make_topic_content(node)
    return request('put', '/posts/' + str(node.discourse_post_id), data)

def _update_topic_metadata(node):
    if node.discourse_topic_id is None:
        return

    data = {}
    data['title'] = node.label
    data['parent_guids[]'] = get_parent_guids(node)
    # this shouldn't ever need to be changed once created...
    #data['category_id'] = {'wiki': wiki_category, 'files': file_category, 'nodes': project_category}[node.target_type]
    return request('put', '/t/' + node.guid_id + '/' + str(node.discourse_topic_id), data)

def sync_topic(node):
    if common.in_migration:
        return

    if node.discourse_topic_id is None:
        create_topic(node)
        return

    parent_guids = get_parent_guids(node)
    guids_changed = parent_guids != node.discourse_topic_parent_guids
    # We don't want problems with case, since discourse change case sometimes.
    title_changed = node.label.lower() != node.discourse_topic_title.lower()

    if guids_changed or title_changed:
        if title_changed:
            _update_topic_content(node)
        _update_topic_metadata(node)

        node.discourse_topic_title = node.label
        node.discourse_topic_parent_guids = parent_guids
        node.save()

def get_or_create_topic_id(node):
    if node is None:
        return None
    if node.discourse_topic_id is None:
        create_topic(node)
    return node.discourse_topic_id

def get_topic(node):
    return request('get', '/t/' + str(node.discourse_topic_id) + '.json')

def delete_topic(node):
    if node.discourse_topic_id is None or node.discourse_topic_deleted:
        return

    result = request('delete', '/t/' + str(node.discourse_topic_id) + '.json')

    node.discourse_topic_deleted = True
    node.save()

    return result

def undelete_topic(node):
    if node.discourse_topic_id is None or not node.discourse_topic_deleted:
        return

    result = request('put', '/t/' + str(node.discourse_topic_id) + '/recover')

    node.discourse_topic_deleted = False
    node.save()

    return result
