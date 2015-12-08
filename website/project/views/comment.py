# -*- coding: utf-8 -*-
import collections
import httplib as http
import pytz
import os

from flask import request
from modularodm import Q

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.forms.utils import sanitize

from website import settings
from website.notifications.emails import notify
from website.notifications.constants import PROVIDERS
from website.models import Guid, Comment
from website.files.models.base import File, StoredFileNode
from website.project.decorators import must_be_contributor_or_public
from datetime import datetime
from website.project.model import has_anonymous_link
from website.profile.utils import serialize_user


def resolve_target(node, page, guid):
    if not guid:
        return node
    target = Guid.load(guid)
    if target is None:
        if page == Comment.FILES:
            return File.load(guid)
        raise HTTPError(http.BAD_REQUEST)
    return target.referent


def serialize_comment(comment, auth, anonymous=False):
    node = comment.node

    if not comment.root_target:
        root_id = ''
        title = ''
        comment.is_hidden = True
    else:
        if isinstance(comment.root_target, StoredFileNode):  # File
            root_id = comment.root_target._id
            title = comment.root_target.name
        else:  # Node or comment
            root_id = comment.root_target._id
            title = ''
    if comment.target:
        targetID = getattr(comment.target, 'page_name', comment.target._id)
    else:
        targetID = ''

    return {
        'id': comment._id,
        'author': serialize_user(comment.user, node=node, n_comments=1, anonymous=anonymous),
        'dateCreated': comment.date_created.isoformat(),
        'dateModified': comment.date_modified.isoformat(),
        'page': comment.page,
        'targetId': targetID,
        'rootId': root_id,
        'title': title,
        'provider': comment.root_target.provider if isinstance(comment.root_target, StoredFileNode) else '',
        'content': comment.content,
        'hasChildren': Comment.find(Q('target', 'eq', comment)).count() != 0,
        'canEdit': comment.user == auth.user,
        'modified': comment.modified,
        'isDeleted': comment.is_deleted,
        'isHidden': comment.is_hidden,
        'isAbuse': auth.user and auth.user._id in comment.reports,
    }


def kwargs_to_comment(cid, auth, owner=False):
    comment = Comment.load(cid)
    if comment is None:
        raise HTTPError(http.NOT_FOUND)
    if owner:
        if auth.user != comment.user:
            raise HTTPError(http.FORBIDDEN)
    return comment


@must_be_logged_in
@must_be_contributor_or_public
def add_comment(auth, node, **kwargs):

    if not node.comment_level:
        raise HTTPError(http.BAD_REQUEST)

    if not node.can_comment(auth):
        raise HTTPError(http.FORBIDDEN)
    comment_info = request.get_json()
    page = comment_info.get('page')
    guid = comment_info.get('target')
    target = resolve_target(node, page, guid)

    content = comment_info.get('content', None)
    if content:
        content = sanitize(content.strip())
    if not content:
        raise HTTPError(http.BAD_REQUEST)
    if len(content) > settings.COMMENT_MAXLENGTH:
        raise HTTPError(http.BAD_REQUEST)

    comment = Comment.create(
        auth=auth,
        node=node,
        target=target,
        user=auth.user,
        page=page,
        content=content,
    )
    comment.save()

    context = dict(
        gravatar_url=auth.user.profile_image_url(),
        content=content,
        page_type='file' if page == Comment.FILES else node.project_or_component,
        page_title=comment.root_target.name if page == Comment.FILES else '',
        provider=PROVIDERS[comment.root_target.provider] if page == Comment.FILES else '',
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

    return {
        'comment': serialize_comment(comment, auth)
    }, http.CREATED


def is_reply(target):
    return isinstance(target, Comment)


@must_be_contributor_or_public
def list_comments(auth, node, **kwargs):
    anonymous = has_anonymous_link(node, auth)
    page = request.args.get('page')
    guid = request.args.get('target')
    root_id = request.args.get('rootId')

    target = resolve_target(node, page, guid)
    comments = Comment.find(Q('target', 'eq', target)).sort('date_created')
    n_unread = Comment.find_unread(auth.user, node, page=page, root_id=root_id)

    ret = {
        'comments': [
            serialize_comment(comment, auth, anonymous)
            for comment in comments
        ],
        'nUnread': n_unread
    }

    return ret

@must_be_logged_in
@must_be_contributor_or_public
def edit_comment(cid, auth, **kwargs):

    comment = kwargs_to_comment(cid, auth, owner=True)

    content = request.get_json().get('content').strip()
    content = sanitize(content)
    if not content:
        raise HTTPError(http.BAD_REQUEST)
    if len(content) > settings.COMMENT_MAXLENGTH:
        raise HTTPError(http.BAD_REQUEST)

    comment.edit(
        content=content,
        auth=auth,
        save=True
    )

    return serialize_comment(comment, auth)


@must_be_logged_in
@must_be_contributor_or_public
def delete_comment(cid, auth, **kwargs):
    comment = kwargs_to_comment(cid, auth, owner=True)
    comment.delete(auth=auth, save=True)

    return {}


@must_be_logged_in
@must_be_contributor_or_public
def undelete_comment(cid, auth, **kwargs):
    comment = kwargs_to_comment(cid, auth, owner=True)
    comment.undelete(auth=auth, save=True)

    return {}


def _update_comments_timestamp(auth, node, page=Comment.OVERVIEW, root_id=None):
    if node.is_contributor(auth.user) and page != 'total':
        user_timestamp = auth.user.comments_viewed_timestamp
        node_timestamp = user_timestamp.get(node._id, None)
        # Handle legacy comments_viewed_timestamp format
        if not node_timestamp:
            user_timestamp[node._id] = dict()
        if node_timestamp and isinstance(node_timestamp, datetime):
            overview_timestamp = user_timestamp[node._id]
            user_timestamp[node._id] = dict()
            user_timestamp[node._id][Comment.OVERVIEW] = overview_timestamp
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


@must_be_logged_in
@must_be_contributor_or_public
def report_abuse(cid, auth, **kwargs):

    user = auth.user

    comment = kwargs_to_comment(cid, auth)

    category = request.get_json().get('category')
    text = request.get_json().get('text', '')
    if not category:
        raise HTTPError(http.BAD_REQUEST)

    try:
        comment.report_abuse(user, save=True, category=category, text=text)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}


@must_be_logged_in
@must_be_contributor_or_public
def unreport_abuse(cid, auth, **kwargs):
    user = auth.user

    comment = kwargs_to_comment(cid, auth)

    try:
        comment.unreport_abuse(user, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}
