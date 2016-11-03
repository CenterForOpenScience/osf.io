import common
from .common import DiscourseException, request
from .categories import file_category, wiki_category, project_category
from .groups import get_or_create_group_id

from website import settings

import re
import requests.compat

def _get_project_node(node):
    """Return the project Node of this project, file, or wiki.
    In the case of a project or component, that would be itself.

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki to retrieve the parent node for
    :return Node: the project Node
    """
    try:
        return node.node
    except AttributeError:
        return node

def _escape_markdown(text):
    """Escapes markdown by adding backslashes in front of special markdown symbols.
    :param str text: the string to escape
    :return str: the escaped text
    """
    r = re.compile(r'([\\`*_{}[\]()#+.!-])')
    return r.sub(r'\\\1', text)

def _make_topic_content(node):
    """"Returns a string suitable for describing the object in its topic's first post.

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki to be described
    :return str: the topic content
    """
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

def _get_parent_guids(node):
    """Return a list of all parent guids, starting with the guid of the containing project Node
    So if node is a (project) Node, its own guid will be the first element of the list
    but not so if it is a file or wiki.

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose parent guids will be returned
    :return list: list of the parent Node GUIDs
    """
    parent_guids = []
    parent_node = _get_project_node(node)
    while parent_node:
        parent_guids.append(parent_node._id)
        parent_node = parent_node.parent_node

    return parent_guids

def _create_topic(node, should_save=True):
    """Create a topic in Discourse for the given project/file/wiki
    This will create a new topic each time, even if one has already been created

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki to create a topic for
    :param bool should_save: Whether the function should call node.save()
    :return int: the topic ID of the created topic
    """
    data = {}
    project_node = _get_project_node(node)

    if wiki_category is None:
        categories.load_basic_categories()
        if wiki_category is None:
            raise DiscourseException('Cannot create topic. Discourse did not properly load when the OSF was started. Please ensure Discourse is running.')

    # privacy is completely relegated to the group with the corresponding project_guid
    data['archetype'] = 'regular'

    get_or_create_group_id(project_node, should_save = node != project_node)  # ensure existance of the group
    data['title'] = node.label
    data['raw'] = _make_topic_content(node)
    data['parent_guids[]'] = _get_parent_guids(node)
    data['topic_guid'] = node.guid_id
    data['category'] = {'wiki': wiki_category, 'files': file_category, 'nodes': project_category}[node.target_type]

    result = request('post', '/posts', data)
    topic_id = result['topic_id']

    node.discourse_topic_id = topic_id
    node.discourse_topic_title = data['title']
    node.discourse_topic_parent_guids = data['parent_guids[]']
    node.discourse_post_id = result['id']
    if should_save:
        node.save()

    return topic_id

def _update_topic_content(node):
    """Updates the content of the first post of the project/file/wiki topic

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki to update the topic content of
    """
    if node.discourse_post_id is None:
        return

    data = {}
    data['post[raw]'] = _make_topic_content(node)
    request('put', '/posts/' + str(node.discourse_post_id), data)

def _update_topic_metadata(node):
    """Updates the title and parent_guids list of the project/file/wiki topic

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki to update the topic metadata of
    """
    if node.discourse_topic_id is None:
        return

    data = {}
    data['title'] = node.label
    data['parent_guids[]'] = _get_parent_guids(node)
    # this shouldn't ever need to be changed once created...
    #data['category_id'] = {'wiki': wiki_category, 'files': file_category, 'nodes': project_category}[node.target_type]
    request('put', '/t/' + node.guid_id + '/' + str(node.discourse_topic_id), data)

def sync_topic(node, should_save=True):
    """Sync (and create if necessary) a topic in Discourse for the given project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose topic should be synchronized
    :param bool should_save: Whether the function should call node.save()
    """
    if common.in_migration:
        return

    if node.discourse_topic_id is None:
        _create_topic(node, should_save)
        return

    parent_guids = _get_parent_guids(node)
    guids_changed = parent_guids != node.discourse_topic_parent_guids
    # We don't want problems with case, since discourse change case sometimes.
    title_changed = node.label.lower() != node.discourse_topic_title.lower()

    if guids_changed or title_changed:
        if title_changed:
            _update_topic_content(node)
        _update_topic_metadata(node)

        node.discourse_topic_title = node.label
        node.discourse_topic_parent_guids = parent_guids
        if should_save:
            node.save()

def get_or_create_topic_id(node, should_save=True):
    """Return the Discourse topic ID of the project/file/wiki, creating it if necessary

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose topic ID should be returned
    :param bool should_save: Whether the function should call node.save() if the topic is created
    :return int: the topic ID
    """
    if node is None:
        return None
    if node.discourse_topic_id is None:
        _create_topic(node, should_save)
    return node.discourse_topic_id

def get_topic(node):
    """Return the topic (as a dict) of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose topic should be returned
    :return dict: Dictionary with information about the Discourse topic
    """
    return request('get', '/t/' + str(node.discourse_topic_id) + '.json')

def delete_topic(node, should_save=True):
    """Delete the topic of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose topic should be deleted
    :param bool should_save: Whether the function should call node.save()
    """
    if node.discourse_topic_id is None or node.discourse_topic_deleted:
        return

    request('delete', '/t/' + str(node.discourse_topic_id) + '.json')

    node.discourse_topic_deleted = True
    if should_save:
        node.save()

def undelete_topic(node, should_save=True):
    """Undelete the topic of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage node: the project/file/wiki whose topic should be undeleted
    :param bool should_save: Whether the function should call node.save()
    """
    if node.discourse_topic_id is None or not node.discourse_topic_deleted:
        return

    request('put', '/t/' + str(node.discourse_topic_id) + '/recover')

    node.discourse_topic_deleted = False
    if should_save:
        node.save()
