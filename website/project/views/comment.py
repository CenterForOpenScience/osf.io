# -*- coding: utf-8 -*-
import collections
import httplib as http
import pytz

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.auth.utils import privacy_info_handle

from website import settings
from website.notifications.emails import notify
from website.filters import gravatar
from website.models import Comment
from website.project.decorators import must_be_contributor_or_public
from website.project.signals import comment_added
from datetime import datetime
from website.project.model import has_anonymous_link


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
                        user, use_ssl=True, size=settings.PROFILE_IMAGE_SMALL
                    ),
                    anonymous
                ),

            }
            for user in sorted_users
        ]
    }


def get_comment(cid, auth, owner=False):
    comment = Comment.load(cid)
    if comment is None:
        raise HTTPError(http.NOT_FOUND)
    if owner:
        if auth.user != comment.user:
            raise HTTPError(http.FORBIDDEN)
    return comment

@comment_added.connect
def send_comment_added_notification(comment, auth):
    node = comment.node
    target = comment.target

    context = dict(
        gravatar_url=auth.user.profile_image_url(),
        content=comment.content,
        target_user=target.user if is_reply(target) else None,
        parent_comment=target.content if is_reply(target) else "",
        url=node.absolute_url
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

@must_be_logged_in
@must_be_contributor_or_public
def update_comments_timestamp(auth, node, **kwargs):
    if node.is_contributor(auth.user):
        auth.user.comments_viewed_timestamp[node._id] = datetime.utcnow()
        auth.user.save()
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
