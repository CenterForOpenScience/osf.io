# -*- coding: utf-8 -*-
import collections
import httplib as http
import pytz

from flask import request
from modularodm import Q

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.auth.utils import privacy_info_handle
from framework.forms.utils import sanitize

from website import settings
from website.notifications.emails import notify
from website.filters import gravatar
from website.models import Guid, Comment
from website.project.decorators import must_be_contributor_or_public
from datetime import datetime
from website.project.model import has_anonymous_link
from website.spam_admin.utils import is_spam

def resolve_target(node, guid):

    if not guid:
        return node
    target = Guid.load(guid)
    if target is None:
        raise HTTPError(http.BAD_REQUEST)
    return target.referent


def collect_discussion(target, users=None):

    users = users or collections.defaultdict(list)
    for comment in getattr(target, 'commented', []):
        if not comment.is_deleted:
            users[comment.user].append(comment)
        collect_discussion(comment, users=users)
    return users


@must_be_contributor_or_public
def comment_discussion(auth, node, **kwargs):

    users = collect_discussion(node)
    anonymous = has_anonymous_link(node, auth)
    # Sort users by comment frequency
    # TODO: Allow sorting by recency, combination of frequency and recency
    sorted_users = sorted(
        users.keys(),
        key=lambda item: len(users[item]),
        reverse=True,
    )

    return {
        'discussion': [
            {
                'id': privacy_info_handle(user._id, anonymous),
                'url': privacy_info_handle(user.url, anonymous),
                'fullname': privacy_info_handle(user.fullname, anonymous, name=True),
                'isContributor': node.is_contributor(user),
                'gravatarUrl': privacy_info_handle(
                    gravatar(
                        user, use_ssl=True, size=settings.GRAVATAR_SIZE_DISCUSSION,
                    ),
                    anonymous
                ),

            }
            for user in sorted_users
        ]
    }


def serialize_comment(comment, auth, anonymous=False):
    return {
        'id': comment._id,
        'author': {
            'id': privacy_info_handle(comment.user._id, anonymous),
            'url': privacy_info_handle(comment.user.url, anonymous),
            'name': privacy_info_handle(
                comment.user.fullname, anonymous, name=True
            ),
            'gravatarUrl': privacy_info_handle(
                gravatar(
                    comment.user, use_ssl=True,
                    size=settings.GRAVATAR_SIZE_DISCUSSION
                ),
                anonymous
            ),
        },
        'dateCreated': comment.date_created.isoformat(),
        'dateModified': comment.date_modified.isoformat(),
        'content': comment.content,
        'hasChildren': bool(getattr(comment, 'commented', [])),
        'canEdit': comment.user == auth.user,
        'modified': comment.modified,
        'isDeleted': comment.is_deleted,
        'isAbuse': auth.user and auth.user._id in comment.reports,
    }


def serialize_comments(record, auth, anonymous=False):

    return [
        serialize_comment(comment, auth, anonymous)
        for comment in getattr(record, 'commented', [])
    ]


def get_comment(cid, auth, owner=False):
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

    guid = request.json.get('target')
    target = resolve_target(node, guid)

    content = request.json.get('content').strip()
    content = sanitize(content)
    if not content:
        raise HTTPError(http.BAD_REQUEST)
    if len(content) > settings.COMMENT_MAXLENGTH:
        raise HTTPError(http.BAD_REQUEST)

    comment = Comment.create(
        auth=auth,
        node=node,
        target=target,
        user=auth.user,
        content=content,
    )
    comment.save()

    if is_spam(comment):
        comment.mark_as_possible_spam(save=True)

    context = dict(
        gravatar_url=auth.user.gravatar_url,
        content=content,
        target_user=target.user if is_reply(target) else None,
        parent_comment=target.content if is_reply(target) else "",
        url=node.absolute_url
    )
    time_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    sent_subscribers = notify(
        uid=node._id,
        event="comments",
        user=auth.user,
        node=node,
        timestamp=time_now,
        **context
    )

    if is_reply(target):
        if target.user and target.user not in sent_subscribers:
            notify(
                uid=target.user._id,
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
    guid = request.args.get('target')
    target = resolve_target(node, guid)
    serialized_comments = serialize_comments(target, auth, anonymous)
    n_unread = 0

    if node.is_contributor(auth.user):
        if auth.user.comments_viewed_timestamp is None:
            auth.user.comments_viewed_timestamp = {}
            auth.user.save()
        n_unread = n_unread_comments(target, auth.user)
    return {
        'comments': serialized_comments,
        'nUnread': n_unread
    }


def n_unread_comments(node, user):
    """Return the number of unread comments on a node for a user."""
    default_timestamp = datetime(1970, 1, 1, 12, 0, 0)
    view_timestamp = user.comments_viewed_timestamp.get(node._id, default_timestamp)
    return Comment.find(Q('node', 'eq', node) &
                        Q('user', 'ne', user) &
                        Q('date_created', 'gt', view_timestamp) &
                        Q('date_modified', 'gt', view_timestamp)).count()


@must_be_logged_in
@must_be_contributor_or_public
def edit_comment(auth, **kwargs):

    cid = kwargs.get('cid')
    comment = get_comment(cid, auth, owner=True)

    content = request.json.get('content').strip()
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
    if is_spam(comment):
        comment.mark_as_possible_spam(save=True)

    return serialize_comment(comment, auth)


@must_be_logged_in
@must_be_contributor_or_public
def delete_comment(auth, **kwargs):

    cid = kwargs.get('cid')
    comment = get_comment(cid, auth, owner=True)
    comment.delete(auth=auth, save=True)

    return {}


@must_be_logged_in
@must_be_contributor_or_public
def undelete_comment(auth, **kwargs):

    cid = kwargs.get('comment')
    comment = get_comment(cid, auth, owner=True)
    comment.undelete(auth=auth, save=True)

    return {}


@must_be_logged_in
@must_be_contributor_or_public
def update_comments_timestamp(auth, node, **kwargs):
    if node.is_contributor(auth.user):
        auth.user.comments_viewed_timestamp[node._id] = datetime.utcnow()
        auth.user.save()
        list_comments(**kwargs)
        return {node._id: auth.user.comments_viewed_timestamp[node._id].isoformat()}
    else:
        return {}


@must_be_logged_in
@must_be_contributor_or_public
def report_abuse(auth, **kwargs):

    user = auth.user

    cid = kwargs.get('cid')
    comment = get_comment(cid, auth)

    category = request.json.get('category')
    text = request.json.get('text', '')
    if not category:
        raise HTTPError(http.BAD_REQUEST)

    try:
        comment.report_abuse(user, save=True, category=category, text=text)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}


@must_be_logged_in
@must_be_contributor_or_public
def unreport_abuse(auth, **kwargs):
    user = auth.user

    cid = kwargs.get('cid')
    comment = get_comment(cid, auth)

    try:
        comment.unreport_abuse(user, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}
