# -*- coding: utf-8 -*-
import pytz
from flask import request
from modularodm import Q

from framework.auth.decorators import must_be_logged_in

from website.notifications.constants import PROVIDERS
from website.notifications.emails import notify
from website.models import Comment
from website.project.decorators import must_be_contributor_or_public
from website.project.signals import comment_added, file_moved_node
from datetime import datetime


@file_moved_node.connect
def update_comment_node(file_obj, destination_node):
    Comment.update(Q('root_target', 'eq', file_obj._id), data={'node': destination_node})

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
