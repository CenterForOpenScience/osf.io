import markdown

from osf.models import Guid
from website import settings
from addons.base.signals import file_updated
from osf.models import BaseFileNode, TrashedFileNode
from osf.models import Comment
from osf.models import Node


@file_updated.connect
def update_file_guid_referent(self, target, event_type, payload, user=None):
    if event_type not in ('addon_file_moved', 'addon_file_renamed'):
        return  # Nothing to do

    source, destination = payload['source'], payload['destination']
    source_node, destination_node = Node.load(source['node']['_id']), Node.load(destination['node']['_id'])

    if source['provider'] in settings.ADDONS_BASED_ON_IDS:
        if event_type == 'addon_file_renamed':
            return  # Node has not changed and provider has not changed

        # Must be a move
        if source['provider'] == destination['provider'] and source_node == destination_node:
            return  # Node has not changed and provider has not changed

    file_guids = BaseFileNode.resolve_class(source['provider'], BaseFileNode.ANY).get_file_guids(
        materialized_path=source['materialized'] if source['provider'] != 'osfstorage' else source['path'],
        provider=source['provider'],
        target=source_node
    )

    for guid in file_guids:
        obj = Guid.load(guid)
        if source_node != destination_node and Comment.objects.filter(root_target___id=guid).count() != 0:
            update_comment_node(guid, source_node, destination_node)

        if source['provider'] != destination['provider'] or source['provider'] != 'osfstorage':
            old_file = BaseFileNode.load(obj.referent._id)
            obj.referent = create_new_file(obj, source, destination, destination_node)
            obj.save()
            if old_file and not TrashedFileNode.load(old_file._id):
                old_file.delete()


def create_new_file(obj, source, destination, destination_node):
    # TODO: Remove when materialized paths are fixed in the payload returned from waterbutler
    if not source['materialized'].startswith('/'):
        source['materialized'] = '/' + source['materialized']
    if not destination['materialized'].startswith('/'):
        destination['materialized'] = '/' + destination['materialized']

    if not source['path'].endswith('/'):
        data = dict(destination)
        new_file = BaseFileNode.resolve_class(destination['provider'], BaseFileNode.FILE).get_or_create(destination_node, destination['path'])
        if destination['provider'] != 'osfstorage':
            new_file.update(revision=None, data=data)
    else:
        new_file = find_and_create_file_from_metadata(destination.get('children', []), source, destination, destination_node, obj)
        if not new_file:
            if source['provider'] == 'box':
                new_path = obj.referent.path
            else:
                new_path = obj.referent.materialized_path.replace(source['materialized'], destination['materialized'])
            new_file = BaseFileNode.resolve_class(destination['provider'], BaseFileNode.FILE).get_or_create(destination_node, new_path)
            new_file.name = new_path.split('/')[-1]
            new_file.materialized_path = new_path
    new_file.save()
    return new_file


def find_and_create_file_from_metadata(children, source, destination, destination_node, obj):
    """ Given a Guid obj, recursively search for the metadata of its referent (a file obj)
    in the waterbutler response. If found, create a new addon BaseFileNode with that metadata
    and return the new file.
    """
    for item in children:
        # TODO: Remove when materialized paths are fixed in the payload returned from waterbutler
        if not item['materialized'].startswith('/'):
            item['materialized'] = '/' + item['materialized']

        if item['kind'] == 'folder':
            return find_and_create_file_from_metadata(item.get('children', []), source, destination, destination_node, obj)
        elif item['kind'] == 'file' and item['materialized'].replace(destination['materialized'], source['materialized']) == obj.referent.materialized_path:
            data = dict(item)
            new_file = BaseFileNode.resolve_class(destination['provider'], BaseFileNode.FILE).get_or_create(destination_node, item['path'])
            if destination['provider'] != 'osfstorage':
                new_file.update(revision=None, data=data)
            return new_file


def update_comment_node(root_target_id, source_node, destination_node):
    Comment.objects.filter(root_target___id=root_target_id).update(node=destination_node)
    source_node.save()
    destination_node.save()


def render_email_markdown(content):
    return markdown.markdown(content, extensions=['markdown_del_ins', 'markdown.extensions.tables', 'markdown.extensions.fenced_code'])
