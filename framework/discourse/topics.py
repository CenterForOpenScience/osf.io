import markupsafe
import requests.compat

import framework.discourse.common
from framework.discourse import categories, common
from website import settings

def _get_parent_node(obj):
    """Return the parent Node of this project, file, or wiki.
    In the case of a project or component, that would be itself.

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki to retrieve the parent node for
    :return Node: the parent Node
    """
    try:
        return obj.node
    except AttributeError:
        return obj

def _make_topic_content(obj):
    """"Returns a string suitable for describing the object in its topic's first post.

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki to be described
    :return str: the topic content
    """
    obj_title = {'wiki': 'Wiki page:', 'files': 'File: ', 'nodes': ''}[obj.target_type]
    obj_title += obj.label
    obj_description = {'wiki': 'the wiki page ', 'files': 'the file ', 'nodes': ''}[obj.target_type]
    obj_description += markupsafe.escape(obj.label)

    parent_node = _get_parent_node(obj)
    topic_content = 'This is the discussion topic for ' + obj_description + '.'
    topic_content += '\nRelevant contributors: ' + ', '.join([c.display_full_name() for c in parent_node.contributors[:6]])
    if len(parent_node.contributors) > 6:
        topic_content += '...'

    if obj.target_type == 'files':
        file_url = requests.compat.urljoin(settings.DOMAIN, obj.guid_id)
        topic_content += '\nFile url: ' + file_url

    return topic_content

def get_parent_guids(obj):
    """Return a list of all parent guids, starting with the guid of the containing parent Node
    So if node is a (project) Node, its own guid will be the first element of the list
    but not so if it is a file or wiki.

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki whose parent guids will be returned
    :return list: list of the parent Node GUIDs
    """
    parent_guids = []
    parent_node = _get_parent_node(obj)
    while parent_node:
        parent_guids.append(parent_node._id)
        parent_node = parent_node.parent_node

    return parent_guids

def _create_topic(obj, should_save=True):
    """Create a topic in Discourse for the given project/file/wiki
    This will create a new topic each time, even if one has already been created

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki to create a topic for
    :param bool should_save: Whether the function should call obj.save()
    :return int: the topic ID of the created topic
    """

    if categories.wiki_category is None:
        categories.load_basic_categories()
        if categories.wiki_category is None:
            raise common.DiscourseException('Cannot create topic. Discourse did not properly load when the OSF was started. Please ensure Discourse is running.')

    parent_guids = get_parent_guids(obj)

    data = {
        # privacy is completely relegated to the group with the corresponding project_guid
        'archetype': 'regular',
        'title': obj.label,
        'raw': _make_topic_content(obj),
        'parent_guids[]': parent_guids,
        'topic_guid': obj.guid_id,
        'category': {'wiki': categories.wiki_category, 'files': categories.file_category, 'nodes': categories.project_category}[obj.target_type]
    }

    result = common.request('post', '/posts', data)
    topic_id = result['topic_id']

    obj.discourse_topic_id = topic_id
    obj.discourse_topic_title = obj.label
    obj.discourse_topic_parent_guids = parent_guids
    obj.discourse_post_id = result['id']
    if should_save:
        obj.save()

    return topic_id

def _update_topic_content(obj):
    """Updates the content of the first post of the project/file/wiki topic

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki to update the topic content of
    """
    if obj.discourse_post_id is None:
        return

    data = {
        'post[raw]': _make_topic_content(obj)
    }
    common.request('put', '/posts/' + str(obj.discourse_post_id), data)

def _update_topic_metadata(obj):
    """Updates the title and parent_guids list of the project/file/wiki topic

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki to update the topic metadata of
    """
    if obj.discourse_topic_id is None:
        return

    data = {
        'title': obj.label,
        'parent_guids[]': get_parent_guids(obj)
    }
    common.request('put', '/t/' + obj.guid_id + '/' + str(obj.discourse_topic_id), data)

def sync_topic(obj, should_save=True):
    """Sync (and create if necessary) a topic in Discourse for the given project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki whose topic should be synchronized
    :param bool should_save: Whether the function should call obj.save()
    """
    if framework.discourse.common.in_migration:
        return

    parent_node = _get_parent_node(obj)
    if not parent_node.discourse_project_created:
        framework.discourse.projects.sync_project_details(parent_node)

    if obj.discourse_topic_id is None:
        _create_topic(obj, should_save)
        return

    parent_guids = get_parent_guids(obj)
    guids_changed = parent_guids != obj.discourse_topic_parent_guids
    # We don't want problems with case, since discourse change case sometimes.
    title_changed = obj.label.lower() != obj.discourse_topic_title.lower()

    deletion_changed = obj.is_deleted != obj.discourse_topic_deleted

    if guids_changed or title_changed or deletion_changed:
        if title_changed:
            _update_topic_content(obj)
        if guids_changed or title_changed:
            _update_topic_metadata(obj)

        if deletion_changed:
            if obj.is_deleted:
                delete_topic(obj, False)
            else:
                undelete_topic(obj, False)

        obj.discourse_topic_title = obj.label
        obj.discourse_topic_parent_guids = parent_guids
        if should_save:
            obj.save()

def get_or_create_topic_id(obj, should_save=True):
    """Return the Discourse topic ID of the project/file/wiki, creating it if necessary

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki whose topic ID should be returned
    :param bool should_save: Whether the function should call obj.save() if the topic is created
    :return int: the topic ID
    """
    if obj is None:
        return None
    if obj.discourse_topic_id is None:
        _create_topic(obj, should_save)
    return obj.discourse_topic_id

def get_topic(obj):
    """Return the topic (as a dict) of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki whose topic should be returned
    :return dict: Dictionary with information about the Discourse topic
    """
    return common.request('get', '/t/' + str(obj.discourse_topic_id) + '.json')

def _some_parent_is_deleted(obj):
    parent_node = _get_parent_node(obj)
    while parent_node:
        if parent_node.discourse_project_deleted:
            return True
        parent_node = parent_node.parent_node
    return False

def delete_topic(obj, should_save=True):
    """Delete the topic of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki whose topic should be deleted
    :param bool should_save: Whether the function should call obj.save()
    """
    if obj.discourse_topic_id is None or obj.discourse_topic_deleted or _some_parent_is_deleted(obj):
        return

    common.request('delete', '/t/' + str(obj.discourse_topic_id) + '.json')

    obj.discourse_topic_deleted = True
    if should_save:
        obj.save()

def undelete_topic(obj, should_save=True):
    """Undelete the topic of the project/file/wiki

    :param Node/StoredFileNode/NodeWikiPage obj: the project/file/wiki whose topic should be undeleted
    :param bool should_save: Whether the function should call obj.save()
    """
    if obj.discourse_topic_id is None or not obj.discourse_topic_deleted or _some_parent_is_deleted(obj):
        return

    common.request('put', '/t/' + str(obj.discourse_topic_id) + '/recover')

    obj.discourse_topic_deleted = False
    if should_save:
        obj.save()
