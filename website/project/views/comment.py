# -*- coding: utf-8 -*-
import collections
import httplib as http

from flask import request
from modularodm import Q

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.auth.utils import privacy_info_handle
from framework.forms.utils import sanitize

from website import settings
from website.filters import gravatar
from website.models import Guid, Comment
from website.project.decorators import must_be_contributor_or_public
from datetime import datetime
from website.project.model import has_anonymous_link
from website.project.views.node import _view_project, n_unread_comments, get_all_files


@must_be_contributor_or_public
def view_comments_project(**kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    ret = {
        'comment_target': 'total',
        'comment_target_id': None
    }

    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_contributor_or_public
def view_comments_overview(**kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    ret = {
        'comment_target': 'node',
        'comment_target_id': node._id
    }
    _update_comments_timestamp(auth, node, page='node', root_id=node._id)
    ret.update(_view_project(node, auth, primary=True))
    return ret

@must_be_contributor_or_public
def view_comments_files(**kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    ret = {
        'comment_target': 'files',
        'comment_target_id': None
    }
    _update_comments_timestamp(auth, node, page='files')
    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_contributor_or_public
def view_comments_wiki(**kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    ret = {
        'comment_target': 'wiki',
        'comment_target_id': None
    }
    _update_comments_timestamp(auth, node, page='wiki')
    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_contributor_or_public
def view_comments_single(**kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
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
        if page == 'wiki':
            return node.get_wiki_page(guid, 1)
        raise HTTPError(http.BAD_REQUEST)
    return target.referent


def collect_discussion(target, users=None):

    users = users or collections.defaultdict(list)
    if not getattr(target, 'commented', None) is None:
        for comment in getattr(target, 'commented', []):
            if not comment.is_deleted:
                users[comment.user].append(comment)
            collect_discussion(comment, users=users)
    return users

@must_be_contributor_or_public
def comment_discussion(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    page = request.args.get('page')
    guid = request.args.get('target')

    if page == 'total':
        users = collections.defaultdict(list)
        for comment in getattr(node, 'comment_owner', []) or []:
            if not comment.is_deleted or not comment.is_hidden:
                users[comment.user].append(comment)
    elif guid is None or guid == 'None':
        users = collections.defaultdict(list)
        comments = Comment.find(Q('node', 'eq', node) &
                                Q('page', 'eq', page) &
                                Q('is_deleted', 'eq', False) &
                                Q('is_hidden', 'eq', False)).get_keys()
        for cid in comments:
            comment = Comment.load(cid)
            if not comment.is_deleted or not comment.is_hidden:
                users[comment.user].append(comment)
    else:
        target = resolve_target(node, page, guid)
        users = collect_discussion(target)
    anonymous = has_anonymous_link(node, auth)

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
        'discussion_by_frequency': [
            serialize_discussion(node, user, anonymous)
            for user in sorted_users_frequency
        ],
        'discussion_by_recency': [
            serialize_discussion(node, user, anonymous)
            for user in sorted_users_recency
        ]
    }

def serialize_discussion(node, user, anonymous=False):
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
        )
    }

def serialize_comment(comment, auth, anonymous=False):
    from website.addons.wiki.model import NodeWikiPage
    if isinstance(comment.root_target, NodeWikiPage):
        root_id = comment.root_target.page_name
        title = comment.root_target.page_name
    else:
        root_id = comment.root_target._id
        title = ''
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
        'page': comment.page or 'node',
        'targetId': getattr(comment.target, 'page_name', comment.target._id),
        'rootId': root_id,
        'title': title or comment.root_title,
        'content': comment.content,
        'hasChildren': bool(getattr(comment, 'commented', [])),
        'canEdit': comment.user == auth.user,
        'modified': comment.modified,
        'isDeleted': comment.is_deleted,
        'isHidden': comment.is_hidden,
        'isAbuse': auth.user and auth.user._id in comment.reports,
    }


def serialize_comments(record, auth, anonymous=False):

    return [
        serialize_comment(comment, auth, anonymous)
        for comment in getattr(record, 'commented', [])
    ]


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
    page = request.json.get('page')
    guid = request.json.get('target')
    title = request.json.get('title')
    target = resolve_target(node, page, guid)

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
        page=page,
        content=content,
        root_title=title,
    )
    comment.save()

    return {
        'comment': serialize_comment(comment, auth)
    }, http.CREATED


@must_be_contributor_or_public
def list_comments(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    anonymous = has_anonymous_link(node, auth)
    page = request.args.get('page')
    guid = request.args.get('target')
    root_id = request.args.get('rootId')

    if page == 'total' and root_id == 'None':    # "Total" on discussion page
        serialized_comments = list_total_comments(node, auth, 'total')
    elif page == 'total':    # Discussion widget on overview's page
        serialized_comments = [
            serialize_comment(comment, auth, anonymous)
            for comment in getattr(node, 'comment_owner', [])
        ]
    elif root_id == 'None':    # Overview/Files/Wiki page on discussion page
        serialized_comments = list_total_comments(node, auth, page)
    else:
        target = resolve_target(node, page, guid)
        serialized_comments = serialize_comments(target, auth, anonymous)
    n_unread = 0

    if node.is_contributor(auth.user):
        if auth.user.comments_viewed_timestamp is None:
            auth.user.comments_viewed_timestamp = {}
            auth.user.save()
        n_unread = n_unread_comments(node, auth.user, page, root_id)

    return {
        'comments': serialized_comments,
        'nUnread': n_unread
    }

def list_total_comments(node, auth, page):
    comments = []
    if page == 'total':
        comments = Comment.find(Q('node', 'eq', node) &
                                Q('is_hidden', 'eq', False) &
                                Q('page', 'ne', 'files')).get_keys()
    elif page != 'files':
        comments = Comment.find(Q('node', 'eq', node) &
                                Q('page', 'eq', page) &
                                Q('is_hidden', 'eq', False)).get_keys()
    serialized_comments = []
    for cid in comments:
        cmt = Comment.load(cid)
        if not isinstance(cmt.target, Comment):
            serialized_comments.append(cmt)
    if page in ('total', 'files'):
        serialized_comments.extend(get_files_comments(node))
    serialized_comments = [
        serialize_comment(comment, auth)
        for comment in serialized_comments
    ]
    serialized_comments = sorted(
        serialized_comments,
        key=lambda item: item.get('dateCreated'),
        reverse=False,
    )
    return serialized_comments

def get_files_comments(node):
    comments = []
    files = get_all_files(node)
    for file_obj in files:
        for comment in getattr(file_obj, 'commented', []):
            if comment.is_hidden:  # File is already deleted
                break
            comments.append(comment)
    return comments

@must_be_logged_in
@must_be_contributor_or_public
def edit_comment(**kwargs):

    auth = kwargs['auth']

    comment = kwargs_to_comment(kwargs, owner=True)

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
        if not auth.user.comments_viewed_timestamp.get(node._id, None):
            auth.user.comments_viewed_timestamp[node._id] = dict()
        if auth.user.comments_viewed_timestamp.get(node._id, None) and \
                isinstance(auth.user.comments_viewed_timestamp[node._id], datetime):
            overview_timestamp = auth.user.comments_viewed_timestamp[node._id]
            auth.user.comments_viewed_timestamp[node._id] = dict()
            auth.user.comments_viewed_timestamp[node._id]['node'] = overview_timestamp
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
        from website.addons.wiki.model import NodeWikiPage
        if root_id is None or root_id == 'None':
            ret = {}
            if page == 'files':
                files = get_all_files(node)
                for addon_file in files:
                    if hasattr(addon_file, 'commented'):
                        ret = _update_comments_timestamp(auth, node, page, addon_file._id)
            elif page == 'wiki':
                root_targets = NodeWikiPage.find(Q('node', 'eq', node)).get_keys()
                for root_target in root_targets:
                    wiki_page = NodeWikiPage.load(root_target)
                    if hasattr(wiki_page, 'commented'):
                        ret = _update_comments_timestamp(auth, node, page, wiki_page.page_name)
            return ret

        # if updating timestamp on a specific file/wiki page
        timestamps[page][root_id] = datetime.utcnow()
        auth.user.save()
        return {node._id: auth.user.comments_viewed_timestamp[node._id][page][root_id].isoformat()}
    else:
        return {}


@must_be_logged_in
@must_be_contributor_or_public
def update_comments_timestamp(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    page = request.json.get('page')
    root_id = request.json.get('rootId')
    return _update_comments_timestamp(auth, node, page, root_id)


@must_be_logged_in
@must_be_contributor_or_public
def report_abuse(**kwargs):

    auth = kwargs['auth']
    user = auth.user

    comment = kwargs_to_comment(kwargs)

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
def unreport_abuse(**kwargs):

    auth = kwargs['auth']
    user = auth.user

    comment = kwargs_to_comment(kwargs)

    try:
        comment.unreport_abuse(user, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}
