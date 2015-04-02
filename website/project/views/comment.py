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
from website.addons.base import GuidFile
from website.project.decorators import must_be_contributor_or_public
from datetime import datetime
from website.project.model import has_anonymous_link
from website.project.views.node import _view_project, n_unread_comments


@must_be_contributor_or_public
def view_comments_project(auth, **kwargs):
    """
    Returns information needed to get comments for the total discussion page
    """

    node = kwargs['node'] or kwargs['project']
    page = request.args.get('page', None)

    if not page:
        ret = _view_comments_total()
    elif page == Comment.OVERVIEW:
        ret = _view_comments_overview(auth, node)
    elif page == Comment.FILES:
        ret = _view_comments_files(auth, node)
    elif page == Comment.WIKI:  # Wiki
        ret = _view_comments_wiki(auth, node)
    else:
        raise HTTPError(http.BAD_REQUEST)
    ret.update(_view_project(node, auth, primary=True, check_files=(not page)))
    return ret


def _view_comments_total():
    return {
        'comment_target': 'total',
        'comment_target_id': None
    }


def _view_comments_overview(auth, node):
    _update_comments_timestamp(auth, node, page='node', root_id=node._id)
    return {
        'comment_target': 'node',
        'comment_target_id': node._id
    }


def _view_comments_files(auth, node):
    _update_comments_timestamp(auth, node, page=Comment.FILES)
    return {
        'comment_target': Comment.FILES,
        'comment_target_id': None
    }


def _view_comments_wiki(auth, node):
    """
    Returns information needed to get comments for the discussion total wiki page
    """
    _update_comments_timestamp(auth, node, page=Comment.WIKI)
    return {
        'comment_target': Comment.WIKI,
        'comment_target_id': None
    }


@must_be_contributor_or_public
def view_comments_single(auth, **kwargs):
    """
    Returns information needed to get a single comment and its replies
    """
    node = kwargs['node'] or kwargs['project']
    comment = kwargs_to_comment(kwargs)
    serialized_comment = serialize_comment(comment, auth)

    from website.addons.wiki.model import NodeWikiPage

    ret = {
        'comment': serialized_comment,
        'comment_target': serialized_comment['page'],
        'comment_target_id': comment.root_target.page_name
        if isinstance(comment.root_target, NodeWikiPage)
        else comment.root_target._id
    }
    ret.update(_view_project(node, auth, primary=True))
    return ret


def resolve_target(node, page, guid):
    if not guid:
        return node
    target = Guid.load(guid)
    if target is None:
        if page == Comment.WIKI:
            return node.get_wiki_page(guid, 1)
        raise HTTPError(http.BAD_REQUEST)
    return target.referent


def collect_discussion(target, users):
    if not getattr(target, 'commented', None) is None:
        for comment in getattr(target, 'commented', []):
            if not (comment.is_deleted or comment.is_hidden):
                users[comment.user].append(comment)
            collect_discussion(comment, users=users)
    return users


def comment_discussion(comments, node, anonymous=False, widget=False):

    users = collections.defaultdict(list)
    for comment in comments:
        if not (comment.is_deleted or comment.is_hidden):
            users[comment.user].append(comment)
        if not widget:
            collect_discussion(comment, users=users)

    sorted_users_frequency = sorted(
        users.keys(),
        key=lambda item: len(users[item]),
        reverse=True,
    )

    def get_recency(item):
        most_recent = users[item][0].date_created
        for comment in users[item][1:]:
            if comment.date_created > most_recent:
                most_recent = comment.date_created
        return most_recent

    sorted_users_recency = sorted(
        users.keys(),
        key=lambda item: get_recency(item),
        reverse=True,
    )

    return {
        'discussionByFrequency': [
            serialize_discussion(node, user, len(users[user]), anonymous)
            for user in sorted_users_frequency
        ],
        'discussionByRecency': [
            serialize_discussion(node, user, len(users[user]), anonymous)
            for user in sorted_users_recency
        ]
    }


def serialize_discussion(node, user, num, anonymous=False):
    return {
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
        'numOfComments': num
    }


def serialize_comment(comment, auth, anonymous=False):
    node = comment.node
    if hasattr(comment.root_target, 'page_name'):  # Wiki
        # In case the wiki name is changed
        root_id = comment.root_target.page_name
        title = comment.root_target.page_name
    elif isinstance(comment.root_target, GuidFile):  # File
        root_id = comment.root_target._id
        title = comment.root_target.waterbutler_path
    else:  # Node or comment
        root_id = comment.root_target._id
        title = ''
    return {
        'id': comment._id,
        'author': serialize_discussion(node, comment.user, 1, anonymous),
        'dateCreated': comment.date_created.isoformat(),
        'dateModified': comment.date_modified.isoformat(),
        'page': comment.page or Comment.OVERVIEW,
        'targetId': getattr(comment.target, 'page_name', comment.target._id),
        'rootId': root_id,
        'title': title,
        'provider': comment.root_target.provider if isinstance(comment.root_target, GuidFile) else '',
        'content': comment.content,
        'hasChildren': bool(getattr(comment, 'commented', [])),
        'canEdit': comment.user == auth.user,
        'modified': comment.modified,
        'isDeleted': comment.is_deleted,
        'isHidden': comment.is_hidden,
        'isAbuse': auth.user and auth.user._id in comment.reports,
    }


def kwargs_to_comment(kwargs, owner=False):
    comment = Comment.load(kwargs.get('cid'))
    if comment is None:
        raise HTTPError(http.BAD_REQUEST)

    if owner:
        auth = kwargs['auth']
        if auth.user != comment.user:
            raise HTTPError(http.FORBIDDEN)

    return comment


@must_be_logged_in
@must_be_contributor_or_public
def add_comment(**kwargs):
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']

    if not node.comment_level:
        raise HTTPError(http.BAD_REQUEST)

    if not node.can_comment(auth):
        raise HTTPError(http.FORBIDDEN)
    comment_info = request.get_json()
    page = comment_info.get('page')
    guid = comment_info.get('target')
    target = resolve_target(node, page, guid)

    content = comment_info.get('content').strip()
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
        page=page,
        content=content,
    )
    comment.save()

    context = dict(
        node_type=node.project_or_component,
        timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
        commenter=auth.user,
        gravatar_url=auth.user.gravatar_url,
        content=content,
        target_user=target.user if is_reply(target) else None,
        parent_comment=target.content if is_reply(target) else "",
        title=node.title,
        node_id=node._id,
        url=node.absolute_url
    )
    sent_subscribers = notify(uid=node._id, event="comments", **context)

    if is_reply(target):
        if target.user and target.user not in sent_subscribers:
            notify(uid=target.user._id, event='comment_replies', **context)

    return {
        'comment': serialize_comment(comment, auth)
    }, http.CREATED


def is_reply(target):
    return isinstance(target, Comment)


@must_be_contributor_or_public
def list_comments(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    anonymous = has_anonymous_link(node, auth)
    page = request.args.get('page')
    guid = request.args.get('target')
    root_id = request.args.get('rootId')
    is_list = request.args.get('isCommentList')
    is_widget = False

    if page == 'total' and not root_id:  # "Total" on discussion page
        comments = list_total_comments(node, auth, 'total')
    elif page == 'total':  # Discussion widget on overview's page
        comments = list_total_comments_widget(node, auth)
        is_widget = True
    elif not root_id:  # Overview/Files/Wiki page on discussion page
        comments = list_total_comments(node, auth, page)
    else:
        target = resolve_target(node, page, guid)
        comments = getattr(target, 'commented', [])

    if is_list:
        discussions = comment_discussion(comments, node, anonymous=anonymous, widget=is_widget)

    n_unread = 0
    if node.is_contributor(auth.user):
        if auth.user.comments_viewed_timestamp is None:
            auth.user.comments_viewed_timestamp = {}
            auth.user.save()
        n_unread = n_unread_comments(node, auth.user, page, root_id)

    ret = {
        'comments': [
            serialize_comment(comment, auth, anonymous)
            for comment in comments
        ],
        'nUnread': n_unread
    }
    if is_list:
        ret.update(discussions)
    return ret


def list_total_comments_widget(node, auth):
    comments_keys = Comment.find(Q('node', 'eq', node)).get_keys()
    comments = []
    for cid in comments_keys:
        cmt = Comment.load(cid)
        comments.append(cmt)
    comments.sort(
        key=lambda item: item.date_created,
        reverse=False
    )
    return comments


def list_total_comments(node, auth, page):
    if page == 'total':
        comments_keys = Comment.find(Q('node', 'eq', node)).get_keys()
    else:
        comments_keys = Comment.find(Q('node', 'eq', node) &
                                Q('page', 'eq', page)).get_keys()
    comments = []
    for cid in comments_keys:
        cmt = Comment.load(cid)
        if not isinstance(cmt.target, Comment):
            comments.append(cmt)
    comments = sorted(
        comments,
        key=lambda item: item.date_created,
        reverse=False,
    )
    return comments


@must_be_logged_in
@must_be_contributor_or_public
def edit_comment(**kwargs):
    auth = kwargs['auth']

    comment = kwargs_to_comment(kwargs, owner=True)

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
def delete_comment(**kwargs):
    auth = kwargs['auth']
    comment = kwargs_to_comment(kwargs, owner=True)
    comment.delete(auth=auth, save=True)

    return {}


@must_be_logged_in
@must_be_contributor_or_public
def undelete_comment(**kwargs):
    auth = kwargs['auth']
    comment = kwargs_to_comment(kwargs, owner=True)
    comment.undelete(auth=auth, save=True)

    return {}


def _update_comments_timestamp(auth, node, page='node', root_id=None):
    if node.is_contributor(auth.user) and page != 'total':
        user_timestamp = auth.user.comments_viewed_timestamp
        if not user_timestamp.get(node._id, None):
            user_timestamp[node._id] = dict()
        node_timestamp = user_timestamp.get(node._id, None)
        if node_timestamp and isinstance(node_timestamp, datetime):
            overview_timestamp = user_timestamp[node._id]
            user_timestamp[node._id] = dict()
            user_timestamp[node._id]['node'] = overview_timestamp
        timestamps = auth.user.comments_viewed_timestamp[node._id]

        # update node timestamp
        if page == 'node':
            timestamps['node'] = datetime.utcnow()
            auth.user.save()
            return {node._id: auth.user.comments_viewed_timestamp[node._id]['node'].isoformat()}

        # set up timestamp dictionary for wiki/files page
        if not timestamps.get(page, None):
            timestamps[page] = dict()

        # if updating timestamp on the files/wiki total page...
        if root_id is None:
            return _update_comments_timestamp_total(node, auth, page)

        # if updating timestamp on a specific file/wiki page
        timestamps[page][root_id] = datetime.utcnow()
        auth.user.save()
        return {node._id: auth.user.comments_viewed_timestamp[node._id][page][root_id].isoformat()}
    else:
        return {}


def _update_comments_timestamp_total(node, auth, page):
    from website.addons.wiki.model import NodeWikiPage
    ret = {}
    if page == Comment.FILES:
        root_targets = node.commented_files.keys()
        for root_target_id in root_targets:
            root_target = Guid.load(root_target_id).referent
            if root_target.commented[0].is_hidden:
                continue
            ret = _update_comments_timestamp(auth, node, page, root_target._id)
    elif page == Comment.WIKI:
        root_targets = NodeWikiPage.find(Q('node', 'eq', node)).get_keys()
        for root_target in root_targets:
            wiki_page = NodeWikiPage.load(root_target)
            if hasattr(wiki_page, 'commented'):
                ret = _update_comments_timestamp(auth, node, page, wiki_page.page_name)
    return ret


@must_be_logged_in
@must_be_contributor_or_public
def update_comments_timestamp(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    timestamp_info = request.get_json()
    page = timestamp_info.get('page')
    root_id = timestamp_info.get('rootId')
    return _update_comments_timestamp(auth, node, page, root_id)


@must_be_logged_in
@must_be_contributor_or_public
def report_abuse(**kwargs):
    auth = kwargs['auth']
    user = auth.user

    comment = kwargs_to_comment(kwargs)

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
def unreport_abuse(**kwargs):
    auth = kwargs['auth']
    user = auth.user

    comment = kwargs_to_comment(kwargs)

    try:
        comment.unreport_abuse(user, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}
