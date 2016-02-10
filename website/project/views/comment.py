# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.auth.decorators import must_be_logged_in

from website.addons.base.signals import file_updated
from website.files.models import FileNode, TrashedFileNode
from website.notifications.constants import PROVIDERS
from website.notifications.emails import notify
from website.models import Comment
from website.project.decorators import must_be_contributor_or_public
from website.project.model import Node
from website.project.signals import comment_added

@file_updated.connect
def update_comment_root_target_file(self, node, event_type, payload, user=None):
    if event_type == 'addon_file_moved' or event_type == 'addon_file_renamed':
        source = payload['source']
        destination = payload['destination']
        source_node = Node.load(source['node']['_id'])
        destination_node = node

        if event_type == 'addon_file_renamed' and (source['provider'] == 'osfstorage' or source['provider'] == 'box'):
            return

        if event_type == 'addon_file_moved' and (source['provider'] == destination['provider'] == ('osfstorage' or 'box')) \
                and source_node == destination_node:
            return

        if source.get('path').endswith('/'):
            if source['provider'] == 'osfstorage':
                folder = FileNode.load(source.get('path').strip('/'))
                update_osffolder_contents(folder.children, source_node, destination_node)
            else:
                folder_contents = destination.get('children', [destination])
                update_folder_contents(folder_contents, source, source_node, destination, destination_node)

        else:
            if source.get('provider') == 'osfstorage':
                try:
                    old_file = TrashedFileNode.find_one(Q('provider', 'eq', source.get('provider')) &
                                                        Q('node', 'eq', source_node) &
                                                        Q('path', 'eq', source.get('path')))
                except NoResultsFound:
                    old_file = FileNode.load(source.get('path').strip('/'))
                else:
                    old_file = old_file.restore()
            else:
                old_file = FileNode.resolve_class(source.get('provider'), FileNode.FILE).get_or_create(source_node, source.get('path'))

            data = dict(destination)  # convert OrderedDict to dict
            data['extra'] = dict(destination['extra'])

            has_comments = Comment.find(Q('root_target', 'eq', old_file._id)).count()
            if has_comments:
                if source['provider'] != 'osfstorage':
                    if destination['provider'] == 'osfstorage':
                        new_file = FileNode.load(destination['path'].strip('/'))
                        update_comment_target(old_file, new_file)
                    else:
                        old_file.update(revision=None, data=data)
                elif destination['provider'] != 'osfstorage':
                    new_file = FileNode.resolve_class(destination.get('provider'), FileNode.FILE).get_or_create(destination_node, destination.get('path'))
                    new_file.update(revision=None, data=data)
                    new_file.stored_object.path = destination['path']
                    new_file.save()
                    update_comment_target(old_file, new_file)

                if source_node._id != destination_node._id:
                    old_file.node = destination_node
                    update_comment_node(old_file, source_node, destination_node)

                if source['provider'] != destination['provider']:
                    old_file.stored_object.provider = destination['provider']

                new_path = destination['path']
                if destination['provider'] == 'dropbox':  # prepend root folder
                    new_path = '{}/{}'.format(destination_node.get_addon(destination['provider']).folder, new_path.strip('/'))

                old_file.stored_object.path = new_path
                old_file.save()


def update_osffolder_contents(folder_contents, source_node, destination_node):
    for item in folder_contents:
        if item.kind == 'folder':
            folder = FileNode.load(item.path.strip('/'))
            update_osffolder_contents(folder.children, source_node, destination_node)
        else:
            item.node = destination_node
            item.save()
            update_comment_node(item, source_node, destination_node)


def update_folder_contents(folder_contents, source, source_node, destination, destination_node):
    for item in folder_contents:
        old_path = item['materialized'].replace(destination['materialized'], source['materialized'])
        if item['kind'] == 'folder':
            subfolder_contents = get_folder_contents(source['provider'], source_node, old_path)
            update_subfolder_contents(subfolder_contents, source, source_node, destination, destination_node)
        else:
            try:
                file_obj = FileNode.find_one(Q('provider', 'eq', source['provider']) &
                                             Q('node', 'eq', source_node) &
                                             Q('materialized_path', 'startswith', old_path))
            except NoResultsFound:
                continue  # something screwed up

            new_path = file_obj.stored_object.path.replace(source['path'], destination['path'])
            if source_node != destination_node:
                file_obj.node = destination_node
                update_comment_node(file_obj, source_node, destination_node)
                new_path = new_path.replace(source_node.get_addon(source['provider']).folder, destination_node.get_addon(destination['provider']).folder)
            data = dict(item)  # convert OrderedDict to dict
            data['extra'] = dict(item['extra'])
            file_obj.update(revision=None, data=data)
            file_obj.path = new_path
            file_obj.save()


def update_subfolder_contents(folder_contents, source, source_node, destination, destination_node):
    for file_obj in folder_contents:
        if file_obj.kind == 'file':
            new_path = file_obj.stored_object.path.replace(source['path'], destination['path'])
            if source_node != destination_node:
                file_obj.node = destination_node
                update_comment_node(file_obj, source_node, destination_node)
                new_path = new_path.replace(source_node.get_addon(source['provider']).folder, destination_node.get_addon(destination['provider']).folder)
            if source['provider'] != destination['provider']:
                file_obj.provider = destination['provider']
            file_obj.path = new_path
            file_obj.save()


def get_folder_contents(provider, node, materialized_path):
    return FileNode.find(Q('provider', 'eq', provider) &
                         Q('node', 'eq', node) &
                         Q('materialized_path', 'startswith', materialized_path))


def update_comment_node(root_target, source_node, destination_node):
    Comment.update(Q('root_target', 'eq', root_target._id), data={'node': destination_node})
    destination_node.commented_files[root_target._id] = source_node.commented_files[root_target._id]
    del source_node.commented_files[root_target._id]
    source_node.save()
    destination_node.save()


def update_comment_target(old_target, new_target):
    Comment.update(Q('root_target', 'eq', old_target._id), data={'root_target': new_target})
    Comment.update(Q('target', 'eq', old_target._id), data={'target': new_target})


@comment_added.connect
def send_comment_added_notification(comment, auth):
    node = comment.node
    target = comment.target

    context = dict(
        gravatar_url=auth.user.profile_image_url(),
        content=comment.content,
        page_type='file' if comment.page == Comment.FILES else node.project_or_component,
        page_title=comment.root_target.name if comment.page == Comment.FILES else '',
        provider=PROVIDERS[comment.root_target.provider] if comment.page == Comment.FILES else '',
        target_user=target.user if is_reply(target) else None,
        parent_comment=target.content if is_reply(target) else "",
        url=comment.get_comment_page_url()
    )
    time_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    sent_subscribers = notify(
        event="comments",
        user=auth.user,
        node=node,
        timestamp=time_now,
        **context
    )

    if is_reply(target):
        if target.user and target.user not in sent_subscribers:
            notify(
                event='comment_replies',
                user=auth.user,
                node=node,
                timestamp=time_now,
                **context
            )


def is_reply(target):
    return isinstance(target, Comment)


def _update_comments_timestamp(auth, node, page=Comment.OVERVIEW, root_id=None):
    if node.is_contributor(auth.user):
        user_timestamp = auth.user.comments_viewed_timestamp
        node_timestamp = user_timestamp.get(node._id, None)
        if not node_timestamp:
            user_timestamp[node._id] = dict()
        timestamps = auth.user.comments_viewed_timestamp[node._id]

        # update node timestamp
        if page == Comment.OVERVIEW:
            timestamps[Comment.OVERVIEW] = datetime.utcnow()
            auth.user.save()
            return {node._id: auth.user.comments_viewed_timestamp[node._id][Comment.OVERVIEW].isoformat()}

        # set up timestamp dictionary for files page
        if not timestamps.get(page, None):
            timestamps[page] = dict()

        # if updating timestamp on a specific file page
        timestamps[page][root_id] = datetime.utcnow()
        auth.user.save()
        return {node._id: auth.user.comments_viewed_timestamp[node._id][page][root_id].isoformat()}
    else:
        return {}

@must_be_logged_in
@must_be_contributor_or_public
def update_comments_timestamp(auth, node, **kwargs):
    timestamp_info = request.get_json()
    page = timestamp_info.get('page')
    root_id = timestamp_info.get('rootId')
    return _update_comments_timestamp(auth, node, page, root_id)
