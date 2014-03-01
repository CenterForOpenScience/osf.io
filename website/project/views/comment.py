# -*- coding: utf-8 -*-
import httplib as http
import logging

from framework import request, User, status
from framework.auth.decorators import collect_auth
from framework.auth.utils import parse_name
from framework.exceptions import HTTPError
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public

from framework.forms.utils import sanitize
from website.models import Guid, Comment


logger = logging.getLogger(__name__)

def resolve_target(node, guid):

    if guid is None:
        return node
    target = Guid.load(guid)
    if target is None:
        raise HTTPError(http.BAD_REQUEST)
    return target.referent


def serialize_comment(comment, node, auth):

    return {
        'author': {
            'id': comment.user._id,
            'name': comment.user.fullname,
        },
        'date': comment.date.strftime('%c'),
        'content': comment.content,
        'isPublic': comment.is_public,
        'canEdit': comment.user == auth.user,
        'canDelete': node.can_edit(auth),
    }


def can_view_comment(comment, node, auth):

    if comment.is_public:
        return True

    return node.can_edit(auth)


def serialize_comments(record, node, auth):

    return [
        serialize_comment(comment, node, auth)
        for comment in record.commented
        if can_view_comment(comment, node, auth)
    ]


@must_be_contributor_or_public
def add_comment(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']

    if not node.can_comment(auth):
        raise HTTPError(http.BAD_REQUEST)

    guid = request.json.get('target')
    target = resolve_target(node, guid)

    content = request.json.get('content')
    if content is None:
        raise HTTPError(http.BAD_REQUEST)
    content = sanitize(content)

    is_public = request.json.get('isPublic')
    if is_public is None:
        raise HTTPError(http.BAD_REQUEST)

    comment = Comment(
        target=target,
        user=auth.user,
        is_public=is_public,
        content=content,
    )
    comment.save()

    return {
        'content': content,
    }, http.CREATED


@must_be_contributor_or_public
def list_comments(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']

    if not node.can_comment(auth):
        return

    guid = request.args.get('target')
    target = resolve_target(node, guid)

    return {
        'comments': serialize_comments(target, node, auth),
    }

@must_be_contributor_or_public
def edit_comment(**kwargs):
    pass

@must_be_contributor_or_public
def delete_comment(**kwargs):
    pass

@must_be_contributor_or_public
def report_comment(**kwargs):
    pass
